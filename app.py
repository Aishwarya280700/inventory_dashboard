import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load data
@st.cache_data
def load_data():
    base_stock = pd.read_excel("base_stock.xlsx")
    lfp_ev_bom = pd.read_excel("lfp_ev_bom.xlsx")
    lfp_ess_bom = pd.read_excel("lfp_ess_bom.xlsx")
    nmc_gen2_bom = pd.read_excel("nmc_gen2_bom.xlsx")
    return base_stock, lfp_ev_bom, lfp_ess_bom, nmc_gen2_bom

base_stock_df, lfp_ev_df, lfp_ess_df, nmc_gen2_df = load_data()

# Combine BOMs into one DataFrame with a Project column
lfp_ev_df['Project'] = 'LFP EV'
lfp_ess_df['Project'] = 'LFP ESS'
nmc_gen2_df['Project'] = 'NMC Gen 2'
bom_df = pd.concat([lfp_ev_df, lfp_ess_df, nmc_gen2_df], ignore_index=True)

# Calculate total required quantity per product across projects
total_required = bom_df.groupby('ProductCode')['RequiredQuantity'].sum().reset_index()
total_required.rename(columns={'RequiredQuantity':'TotalRequired'}, inplace=True)

# Merge with base_stock to find low stock items
stock_status = pd.merge(base_stock_df, total_required, on='ProductCode', how='left')
stock_status['TotalRequired'].fillna(0, inplace=True)
stock_status['Needs Replenishment'] = stock_status['QuantityAvailable'] < stock_status['TotalRequired']

st.title("Inventory & Project Stock Dashboard")

# Section 1: Admin Stock Management
st.header("Admin: Manage Base Stock")

prod_code = st.selectbox("Select Product Code", base_stock_df['ProductCode'])
qty_change = st.number_input("Add (positive) or Remove (negative) Quantity", value=0, step=1)
if st.button("Update Stock"):
    idx = base_stock_df.index[base_stock_df['ProductCode'] == prod_code][0]
    new_qty = base_stock_df.at[idx, 'QuantityAvailable'] + qty_change
    if new_qty < 0:
        st.error("Stock cannot go below zero!")
    else:
        base_stock_df.at[idx, 'QuantityAvailable'] = new_qty
        st.success(f"Updated {prod_code} stock to {new_qty}")

# Section 2: Issue Stock to Projects
st.header("Project: Issue Stock")

project = st.selectbox("Select Project", ['LFP EV', 'LFP ESS', 'NMC Gen 2'])
proj_bom = bom_df[bom_df['Project'] == project]
proj_product = st.selectbox("Select Product Code", proj_bom['ProductCode'])

max_issue = min(
    base_stock_df.loc[base_stock_df['ProductCode'] == proj_product, 'QuantityAvailable'].values[0],
    proj_bom.loc[proj_bom['ProductCode'] == proj_product, 'RequiredQuantity'].values[0]
)
issue_qty = st.number_input(f"Issue quantity (max {max_issue})", min_value=0, max_value=max_issue, step=1)

if st.button("Issue Stock"):
    if issue_qty > 0 and issue_qty <= max_issue:
        # Update base_stock
        idx_base = base_stock_df.index[base_stock_df['ProductCode'] == proj_product][0]
        base_stock_df.at[idx_base, 'QuantityAvailable'] -= issue_qty
        # Update BOM required quantity for the project
        idx_bom = bom_df.index[(bom_df['Project'] == project) & (bom_df['ProductCode'] == proj_product)][0]
        bom_df.at[idx_bom, 'RequiredQuantity'] -= issue_qty
        st.success(f"Issued {issue_qty} of {proj_product} to {project}")

# Section 3: Products needing replenishment
st.header("Products needing Replenishment")

low_stock = stock_status[stock_status['Needs Replenishment'] == True][['ProductCode','ProductName','QuantityAvailable','TotalRequired']]
st.dataframe(low_stock)

# Section 4: Data Analysis & Graphs
st.header("Inventory Analysis")

# Plot QuantityAvailable vs TotalRequired
fig, ax = plt.subplots(figsize=(10,6))
x = np.arange(len(stock_status))
width = 0.35
ax.bar(x - width/2, stock_status['QuantityAvailable'], width, label='Available')
ax.bar(x + width/2, stock_status['TotalRequired'], width, label='Required')
ax.set_xticks(x)
ax.set_xticklabels(stock_status['ProductCode'], rotation=45)
ax.set_ylabel("Quantity")
ax.set_title("Stock vs Required Quantities")
ax.legend()
st.pyplot(fig)

# Summary stats
st.write("### Summary")
st.write(f"Total unique products: {len(stock_status)}")
st.write(f"Products needing replenishment: {low_stock.shape[0]}")

# Optionally save updated data back to Excel (you can add a button for this)
if st.button("Save Data"):
    base_stock_df.to_excel("base_stock_updated.xlsx", index=False)
    bom_df.to_excel("bom_updated.xlsx", index=False)
    st.success("Data saved to base_stock_updated.xlsx and bom_updated.xlsx")

