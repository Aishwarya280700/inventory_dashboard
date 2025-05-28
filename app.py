import streamlit as st
import pandas as pd
from datetime import datetime

# Load base stock and BOM files
base_stock_df = pd.read_excel("base_stock.xlsx")
lfp_ev_bom_df = pd.read_excel("lfp_ev_bom.xlsx")
lfp_ess_bom_df = pd.read_excel("lfp_ess_bom.xlsx")
nmc_gen2_bom_df = pd.read_excel("nmc_gen2_bom.xlsx")

# Load or create stock log
try:
    stock_log_df = pd.read_excel("stock_log.xlsx")
except FileNotFoundError:
    stock_log_df = pd.DataFrame(columns=[
        'Date', 'Project', 'ProductCode', 'ProductName',
        'Quantity', 'Action', 'PerformedBy'
    ])

# Function to calculate total required quantity for each product across all projects
def get_total_required_qty():
    all_boms = pd.concat([lfp_ev_bom_df, lfp_ess_bom_df, nmc_gen2_bom_df])
    all_boms['RequiredQuantity'] = pd.to_numeric(all_boms['RequiredQuantity'], errors='coerce').fillna(0)
    total_req = all_boms.groupby('ProductCode')['RequiredQuantity'].sum().reset_index()
    return total_req

# Highlight products needing replenishment in base stock df
def highlight_replenishment(row):
    total_req = total_required_dict.get(row['ProductCode'], 0)
    if row['QuantityAvailable'] < total_req:
        return ['background-color: #ff9999']*len(row)
    else:
        return ['']*len(row)

# Calculate total required quantities once (refresh every run)
total_required_df = get_total_required_qty()
total_required_dict = dict(zip(total_required_df['ProductCode'], total_required_df['RequiredQuantity']))

# Select role
st.title("📦 Inventory Dashboard")
role = st.radio("Select Role", ["Admin", "Project User"])

if role == "Admin":
    st.header("🔼 Add or Remove Stock from Base Inventory")
    action = st.selectbox("Action", ["Add Stock", "Remove Stock"])

    with st.form("manage_stock_form"):
        product_code = st.text_input("Product Code")
        quantity = st.number_input("Quantity", min_value=1)
        performed_by = st.text_input("Your Name")
        submitted = st.form_submit_button("Submit")

        if submitted:
            if product_code not in base_stock_df['ProductCode'].values:
                st.error("❌ Product code not found in base stock.")
            else:
                idx = base_stock_df.index[base_stock_df['ProductCode'] == product_code][0]
                if action == "Add Stock":
                    base_stock_df.at[idx, 'QuantityAvailable'] += quantity
                    action_str = "Added"
                    st.success(f"✅ Added {quantity} units to {product_code} in base stock.")
                else:
                    # Remove stock with validation
                    if base_stock_df.at[idx, 'QuantityAvailable'] < quantity:
                        st.error(f"❌ Cannot remove {quantity} units. Only {base_stock_df.at[idx, 'QuantityAvailable']} available.")
                    else:
                        base_stock_df.at[idx, 'QuantityAvailable'] -= quantity
                        action_str = "Removed"
                        st.success(f"✅ Removed {quantity} units from {product_code} in base stock.")

                # Log action if success
                if 'action_str' in locals():
                    new_row = pd.DataFrame([{
                        'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'Project': '',
                        'ProductCode': product_code,
                        'ProductName': base_stock_df.at[idx, 'ProductName'],
                        'Quantity': quantity,
                        'Action': action_str,
                        'PerformedBy': performed_by
                    }])
                    stock_log_df = pd.concat([stock_log_df, new_row], ignore_index=True)

                    # Save changes
                    base_stock_df.to_excel("base_stock.xlsx", index=False)
                    stock_log_df.to_excel("stock_log.xlsx", index=False)

else:
    st.header("🔽 Issue Stock to Project")
    project = st.selectbox("Select Project", ["LFP EV", "LFP ESS", "NMC Gen 2"])
    product_code = st.text_input("Product Code to Issue")
    quantity = st.number_input("Quantity to Issue", min_value=1)
    performed_by = st.text_input("Your Name")
    issue_button = st.button("Issue Stock")

    if issue_button:
        # Validate product in base stock
        if product_code not in base_stock_df['ProductCode'].values:
            st.error("❌ Product code not found in base stock.")
        else:
            base_idx = base_stock_df.index[base_stock_df['ProductCode'] == product_code][0]
            base_qty = base_stock_df.at[base_idx, 'QuantityAvailable']

            # Get BOM df for selected project
            if project == "LFP EV":
                bom_df = lfp_ev_bom_df
                bom_file = "lfp_ev_bom.xlsx"
            elif project == "LFP ESS":
                bom_df = lfp_ess_bom_df
                bom_file = "lfp_ess_bom.xlsx"
            else:
                bom_df = nmc_gen2_bom_df
                bom_file = "nmc_gen2_bom.xlsx"

            # Validate product in BOM
            if product_code not in bom_df['ProductCode'].values:
                st.error(f"❌ Product code not found in {project} BOM.")
            else:
                bom_idx = bom_df.index[bom_df['ProductCode'] == product_code][0]
                required_qty = bom_df.at[bom_idx, 'RequiredQuantity']

                # Check stock and required quantity
                if quantity > base_qty:
                    st.error("❌ Not enough quantity available in base stock.")
                elif quantity > required_qty:
                    st.error(f"❌ Quantity exceeds project required quantity ({required_qty}).")
                else:
                    # Deduct from base stock
                    base_stock_df.at[base_idx, 'QuantityAvailable'] -= quantity
                    # Deduct from project BOM required quantity
                    bom_df.at[bom_idx, 'RequiredQuantity'] -= quantity

                    # Log issue action
                    new_row = pd.DataFrame([{
                        'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'Project': project,
                        'ProductCode': product_code,
                        'ProductName': base_stock_df.at[base_idx, 'ProductName'],
                        'Quantity': quantity,
                        'Action': 'Issued',
                        'PerformedBy': performed_by
                    }])
                    stock_log_df = pd.concat([stock_log_df, new_row], ignore_index=True)

                    # Save all changes
                    base_stock_df.to_excel("base_stock.xlsx", index=False)
                    bom_df.to_excel(bom_file, index=False)
                    stock_log_df.to_excel("stock_log.xlsx", index=False)

                    st.success(f"✅ Issued {quantity} units of {product_code} to {project}.")

# Show current stock and BOM summaries
st.subheader("📋 Current Base Stock (Products needing replenishment are highlighted in red)")

# Apply highlighting for replenishment need
st.dataframe(base_stock_df.style.apply(highlight_replenishment, axis=1))

st.subheader("📁 Current Project BOMs")
st.write("LFP EV BOM")
st.dataframe(lfp_ev_bom_df)
st.write("LFP ESS BOM")
st.dataframe(lfp_ess_bom_df)
st.write("NMC Gen 2 BOM")
st.dataframe(nmc_gen2_bom_df)

st.subheader("🕓 Stock Movement Log")
st.dataframe(stock_log_df)
