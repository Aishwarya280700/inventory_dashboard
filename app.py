import streamlit as st
import pandas as pd

# Helper function to load and clean BOM sheets
def load_bom(filename):
    df = pd.read_excel(filename)
    df['RequiredQuantity'] = pd.to_numeric(df['RequiredQuantity'], errors='coerce').fillna(0)
    return df

# Load base stock
base_stock_df = pd.read_excel("base_stock.xlsx")
base_stock_df['QuantityAvailable'] = pd.to_numeric(base_stock_df['QuantityAvailable'], errors='coerce').fillna(0)

# Load BOMs for projects
bom_files = {
    "LFP EV": "LFP_EV.xlsx",
    "LFP ESS": "LFP_ESS.xlsx",
    "NMC Gen 2": "NMC_Gen2.xlsx"
}
bom_dfs = {proj: load_bom(file) for proj, file in bom_files.items()}

st.title("Inventory Management Dashboard")

# User role selection (simple simulation)
role = st.radio("Select role:", ["Admin", "Project User"])

if role == "Admin":
    st.header("Base Stock Management (Admin)")
    st.dataframe(base_stock_df)

    product_codes = base_stock_df['ProductCode'].tolist()
    product_choice = st.selectbox("Select product to update quantity", product_codes)

    qty_change = st.number_input("Quantity to add (+) or remove (-):", step=1, format="%d")

    if st.button("Update Stock"):
        idx = base_stock_df.index[base_stock_df['ProductCode'] == product_choice][0]
        new_qty = base_stock_df.at[idx, 'QuantityAvailable'] + qty_change
        if new_qty < 0:
            st.error("Quantity cannot be negative!")
        else:
            base_stock_df.at[idx, 'QuantityAvailable'] = new_qty
            base_stock_df.to_excel("base_stock.xlsx", index=False)
            st.success(f"Updated {product_choice} quantity to {new_qty}")

elif role == "Project User":
    st.header("Issue Stock to Project")
    project = st.selectbox("Select Project", list(bom_files.keys()))
    bom_df = bom_dfs[project]

    st.subheader(f"Project BOM - {project}")
    st.dataframe(bom_df)

    # Products in this project with remaining required qty > 0
    bom_df = bom_df[bom_df['RequiredQuantity'] > 0]

    if bom_df.empty:
        st.info("No required quantity pending in this project.")
    else:
        product_codes = bom_df['ProductCode'].tolist()
        product_choice = st.selectbox("Select product to issue", product_codes)

        # Show available quantity in base stock
        qty_available = base_stock_df.loc[base_stock_df['ProductCode'] == product_choice, 'QuantityAvailable'].values
        if len(qty_available) == 0:
            st.error("Product not found in base stock.")
        else:
            qty_available = qty_available[0]
            st.write(f"Quantity Available in Base Stock: {qty_available}")

            # Show required quantity in project
            required_qty = bom_df.loc[bom_df['ProductCode'] == product_choice, 'RequiredQuantity'].values[0]
            st.write(f"Required Quantity in Project: {required_qty}")

            issue_qty = st.number_input("Quantity to issue:", min_value=1, max_value=int(min(qty_available, required_qty)))

            if st.button("Issue Stock"):
                if issue_qty <= 0:
                    st.error("Issue quantity must be positive.")
                elif issue_qty > qty_available:
                    st.error("Not enough stock available.")
                elif issue_qty > required_qty:
                    st.error("Issue quantity cannot exceed required quantity.")
                else:
                    # Deduct from base stock
                    base_idx = base_stock_df.index[base_stock_df['ProductCode'] == product_choice][0]
                    base_stock_df.at[base_idx, 'QuantityAvailable'] -= issue_qty

                    # Deduct from BOM required qty
                    bom_idx = bom_df.index[bom_df['ProductCode'] == product_choice][0]
                    bom_df.at[bom_idx, 'RequiredQuantity'] -= issue_qty

                    # Save updated data
                    base_stock_df.to_excel("base_stock.xlsx", index=False)
                    bom_df.to_excel(bom_files[project], index=False)

                    st.success(f"Issued {issue_qty} units of {product_choice} to {project}")

# Show products that need to be restocked (QuantityAvailable < total required quantity across all projects)
st.header("Products Needing Restock")

# Combine all BOMs to get total required qty per product
combined_bom = pd.concat(bom_dfs.values())
combined_bom['RequiredQuantity'] = pd.to_numeric(combined_bom['RequiredQuantity'], errors='coerce').fillna(0)
total_required = combined_bom.groupby('ProductCode')['RequiredQuantity'].sum().reset_index()

# Merge with base stock
stock_vs_req = pd.merge(base_stock_df, total_required, on='ProductCode', how='left')
stock_vs_req['RequiredQuantity'] = stock_vs_req['RequiredQuantity'].fillna(0)

# Filter products needing restock
need_restock = stock_vs_req[stock_vs_req['QuantityAvailable'] < stock_vs_req['RequiredQuantity']]

if need_restock.empty:
    st.write("All products have sufficient stock.")
else:
    st.dataframe(need_restock[['ProductCode', 'ProductName', 'Supplier', 'QuantityAvailable', 'RequiredQuantity']])
