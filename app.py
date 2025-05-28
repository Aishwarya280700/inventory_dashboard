import streamlit as st
import pandas as pd
from datetime import datetime

# Load Excel files
base_stock_df = pd.read_excel("inventory_stock.xlsx")
lfp_ev_bom_df = pd.read_excel("lfp_ev_bom.xlsx")
lfp_ess_bom_df = pd.read_excel("lfp_ess_bom.xlsx")
nmc_gen2_bom_df = pd.read_excel("nmc_gen2_bom.xlsx")
stock_log_df = pd.read_excel("stock_log.xlsx")

# Header
st.title("📦 Inventory Dashboard")
st.markdown("Manage and track stock in and out for multiple projects.")

# Display base stock
st.subheader("📋 Base Stock")
st.dataframe(base_stock_df)

# Project BoMs
st.subheader("📁 Project BoMs")
project_choice = st.selectbox("Choose Project", ["LFP EV", "LFP ESS", "NMC Gen 2"])
if project_choice == "LFP EV":
    st.dataframe(lfp_ev_bom_df)
elif project_choice == "LFP ESS":
    st.dataframe(lfp_ess_bom_df)
elif project_choice == "NMC Gen 2":
    st.dataframe(nmc_gen2_bom_df)

# Add or Issue Stock
st.subheader("🔄 Add / Issue Stock")

with st.form("stock_form"):
    action = st.radio("Action", ["Add", "Issue"])
    project = st.selectbox("Project (only for Issue)", ["", "LFP EV", "LFP ESS", "NMC Gen 2"])
    product_code = st.text_input("Product Code")
    quantity = st.number_input("Quantity", min_value=1)
    performed_by = st.text_input("Your Name")
    submitted = st.form_submit_button("Submit")

    if submitted:
        if product_code not in base_stock_df['ProductCode'].values:
            st.error("Product not found in base stock.")
        else:
            index = base_stock_df[base_stock_df['ProductCode'] == product_code].index[0]
            product_name = base_stock_df.at[index, 'ProductName']
            supplier = base_stock_df.at[index, 'Supplier']
            current_qty = base_stock_df.at[index, 'QuantityAvailable']

            if action == "Add":
                base_stock_df.at[index, 'QuantityAvailable'] += quantity
                stock_log_df = stock_log_df.append({
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Project': "",
                    'ProductCode': product_code,
                    'ProductName': product_name,
                    'Quantity': quantity,
                    'Action': "Added",
                    'PerformedBy': performed_by
                }, ignore_index=True)
                st.success(f"{quantity} units added to {product_code}")

            elif action == "Issue":
                if quantity > current_qty:
                    st.error("Not enough stock to issue.")
                else:
                    base_stock_df.at[index, 'QuantityAvailable'] -= quantity
                    stock_log_df = stock_log_df.append({
                        'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'Project': project,
                        'ProductCode': product_code,
                        'ProductName': product_name,
                        'Quantity': quantity,
                        'Action': "Issued",
                        'PerformedBy': performed_by
                    }, ignore_index=True)
                    st.success(f"{quantity} units issued to {project}")

            # Save updated data
            base_stock_df.to_excel("base_stock.xlsx", index=False)
            stock_log_df.to_excel("stock_log.xlsx", index=False)

# Display stock log
st.subheader("🕓 Stock Movement Log")
st.dataframe(stock_log_df)
