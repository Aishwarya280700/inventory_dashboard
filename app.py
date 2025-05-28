import streamlit as st
import pandas as pd
from datetime import datetime

# --- Simple hardcoded credentials ---
credentials = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user1": {"password": "user123", "role": "Project User"},
    "user2": {"password": "user456", "role": "Project User"}
}

# --- Session state for login ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""

def login():
    st.title("🔐 Inventory Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in credentials and credentials[username]['password'] == password:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.role = credentials[username]['role']
            st.success(f"✅ Welcome, {username} ({st.session_state.role})")
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password.")

def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.experimental_rerun()

# --- Show login if not authenticated ---
if not st.session_state.authenticated:
    login()
    st.stop()

# --- Main app starts below if authenticated ---
st.sidebar.write(f"👤 Logged in as: {st.session_state.username}")
if st.sidebar.button("Logout"):
    logout()

# --- Load Excel files ---
base_stock_df = pd.read_excel("base_stock.xlsx")
lfp_ev_bom_df = pd.read_excel("lfp_ev_bom.xlsx")
lfp_ess_bom_df = pd.read_excel("lfp_ess_bom.xlsx")
nmc_gen2_bom_df = pd.read_excel("nmc_gen2_bom.xlsx")

try:
    stock_log_df = pd.read_excel("stock_log.xlsx")
except FileNotFoundError:
    stock_log_df = pd.DataFrame(columns=[
        'Date', 'Project', 'ProductCode', 'ProductName',
        'Quantity', 'Action', 'PerformedBy'
    ])

# --- Helper functions ---
def get_total_required_qty():
    all_boms = pd.concat([lfp_ev_bom_df, lfp_ess_bom_df, nmc_gen2_bom_df])
    all_boms['RequiredQuantity'] = pd.to_numeric(all_boms['RequiredQuantity'], errors='coerce').fillna(0)
    return all_boms.groupby('ProductCode')['RequiredQuantity'].sum().reset_index()

def highlight_replenishment(row):
    total_req = total_required_dict.get(row['ProductCode'], 0)
    return ['background-color: #ff9999'] * len(row) if row['QuantityAvailable'] < total_req else [''] * len(row)

# --- Compute required quantities ---
total_required_df = get_total_required_qty()
total_required_dict = dict(zip(total_required_df['ProductCode'], total_required_df['RequiredQuantity']))

# --- Main UI ---
st.title("📦 Inventory Dashboard")

if st.session_state.role == "Admin":
    st.header("🔼 Add or Remove Stock from Base Inventory")
    action = st.selectbox("Action", ["Add Stock", "Remove Stock"])

    with st.form("admin_form"):
        product_code = st.text_input("Product Code")
        quantity = st.number_input("Quantity", min_value=1)
        submitted_by = st.session_state.username
        submit = st.form_submit_button("Submit")

        if submit:
            if product_code not in base_stock_df['ProductCode'].values:
                st.error("❌ Product code not found.")
            else:
                idx = base_stock_df.index[base_stock_df['ProductCode'] == product_code][0]
                if action == "Add Stock":
                    base_stock_df.at[idx, 'QuantityAvailable'] += quantity
                    act = "Added"
                    st.success(f"✅ {quantity} units added to {product_code}")
                else:
                    if base_stock_df.at[idx, 'QuantityAvailable'] < quantity:
                        st.error("❌ Not enough stock to remove.")
                        st.stop()
                    base_stock_df.at[idx, 'QuantityAvailable'] -= quantity
                    act = "Removed"
                    st.success(f"✅ {quantity} units removed from {product_code}")

                # Log and save
                new_row = pd.DataFrame([{
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Project': '',
                    'ProductCode': product_code,
                    'ProductName': base_stock_df.at[idx, 'ProductName'],
                    'Quantity': quantity,
                    'Action': act,
                    'PerformedBy': submitted_by
                }])
                stock_log_df = pd.concat([stock_log_df, new_row], ignore_index=True)
                base_stock_df.to_excel("base_stock.xlsx", index=False)
                stock_log_df.to_excel("stock_log.xlsx", index=False)

else:
    st.header("🔽 Issue Stock to Project")
    project = st.selectbox("Project", ["LFP EV", "LFP ESS", "NMC Gen 2"])
    product_code = st.text_input("Product Code")
    quantity = st.number_input("Quantity", min_value=1)
    submitted_by = st.session_state.username

    if st.button("Issue Stock"):
        if product_code not in base_stock_df['ProductCode'].values:
            st.error("❌ Product not found.")
        else:
            base_idx = base_stock_df.index[base_stock_df['ProductCode'] == product_code][0]
            base_qty = base_stock_df.at[base_idx, 'QuantityAvailable']

            if project == "LFP EV":
                bom_df, bom_file = lfp_ev_bom_df, "lfp_ev_bom.xlsx"
            elif project == "LFP ESS":
                bom_df, bom_file = lfp_ess_bom_df, "lfp_ess_bom.xlsx"
            else:
                bom_df, bom_file = nmc_gen2_bom_df, "nmc_gen2_bom.xlsx"

            if product_code not in bom_df['ProductCode'].values:
                st.error("❌ Product not found in BOM.")
            else:
                bom_idx = bom_df.index[bom_df['ProductCode'] == product_code][0]
                required_qty = bom_df.at[bom_idx, 'RequiredQuantity']
                if quantity > base_qty:
                    st.error("❌ Not enough stock.")
                elif quantity > required_qty:
                    st.error("❌ Exceeds required quantity.")
                else:
                    base_stock_df.at[base_idx, 'QuantityAvailable'] -= quantity
                    bom_df.at[bom_idx, 'RequiredQuantity'] -= quantity

                    new_row = pd.DataFrame([{
                        'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'Project': project,
                        'ProductCode': product_code,
                        'ProductName': base_stock_df.at[base_idx, 'ProductName'],
                        'Quantity': quantity,
                        'Action': 'Issued',
                        'PerformedBy': submitted_by
                    }])
                    stock_log_df = pd.concat([stock_log_df, new_row], ignore_index=True)
                    base_stock_df.to_excel("base_stock.xlsx", index=False)
                    bom_df.to_excel(bom_file, index=False)
                    stock_log_df.to_excel("stock_log.xlsx", index=False)
                    st.success(f"✅ Issued {quantity} units to {project}")

# Display current data
st.subheader("📋 Current Base Stock (Replenishment needed highlighted)")
st.dataframe(base_stock_df.style.apply(highlight_replenishment, axis=1))

st.subheader("📁 BOMs")
st.write("🔹 LFP EV")
st.dataframe(lfp_ev_bom_df)
st.write("🔹 LFP ESS")
st.dataframe(lfp_ess_bom_df)
st.write("🔹 NMC Gen 2")
st.dataframe(nmc_gen2_bom_df)

st.subheader("📜 Stock Log")
st.dataframe(stock_log_df)
