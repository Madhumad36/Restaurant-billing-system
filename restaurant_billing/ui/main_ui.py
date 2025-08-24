import os
import sqlite3
import streamlit as st
import pandas as pd
import io
import json
from urllib.parse import quote

import streamlit.components.v1 as components
from utils.db_utils import DB_PATH, fetch_menu, save_order, fetch_orders, setup_database, import_menu_from_csv 
from utils.calculator import get_discount_percent, calc_totals, format_bill_text
from datetime import datetime,date

# --- LOGIN SECTION ---

def check_login(username, password, role):
    username = username.strip().lower()
    password = password.strip()
    role = role.strip().lower()
    if role == "manager":
        return username == "manager" and password == "manager1234"
    elif role == "admin":
        return username == "admin" and password == "admin5678"
    elif role == "cashier":
        return username == "cashier" and password == "cashier000"
    return False

if "login_success" not in st.session_state:
    st.session_state["login_success"] = False

if not st.session_state["login_success"]:
    st.title("Login")
    st.write("Please log in to access the Restaurant Billing System.")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Manager","Admin", "Cashier"])
    login_clicked = st.button("Login")
    if login_clicked:
        if check_login(username, password, role):
            st.session_state["login_success"] = True
            st.session_state["user_role"] = role
            st.success("Login successful! Please wait...")
            st.rerun()
        else:
            st.error("Incorrect credentials. Please try again.")
    st.stop()  

# --- SETUP DATABASE/MENU ---
setup_database()
# Build absolute path to menu.csv
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
menu_csv_path = os.path.join(PROJECT_ROOT, 'data', 'menu.csv')

# Import menu from CSV only if menu table is empty
if len(fetch_menu()) == 0:
    if os.path.exists(menu_csv_path):
        import_menu_from_csv(menu_csv_path)
    else:
        st.error(f"Menu CSV not found at: {menu_csv_path}. Please add data/menu.csv file.")
        st.stop()

menu_data = fetch_menu()
menu_df = pd.DataFrame(menu_data)

required_cols = {'id', 'name', 'category', 'price', 'gst'}
if menu_df.empty or not required_cols.issubset(set(menu_df.columns)):
    st.error("Menu is empty or missing required columns (id, name, category, price, gst). Check data/menu.csv.")
    st.stop()

# --- SIDEBAR ---
st.markdown("""
<style>
/* Reduce excessive vertical padding and margin in sidebar */
section[data-testid="stSidebar"] > div:first-child, /* top spacer */
section[data-testid="stSidebar"] * {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

/* Reduce spacing specifically for selectbox */
section[data-testid="stSidebar"] .stSelectbox {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

/* Reduce spacing for headings and labels in sidebar */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] h5,
section[data-testid="stSidebar"] h6,
section[data-testid="stSidebar"] label {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    line-height: 1.1 !important;
}

/* Tweak hr and headings spacing if desired */
hr, .st-emotion-cache-10trblm { margin: 0.2rem 0 !important; }
</style>
""", unsafe_allow_html=True)
# Sidebar content
with st.sidebar:
    st.image("logo.jpg", width=180)
    st.markdown(
        "<div style='text-align:center; color:#ffffff; font-size:1.1em; font-weight:bold; margin-bottom:18px;'>Fresh. Simple. Delicious.</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    if "user_role" in st.session_state:
        st.markdown(
            f"<span style='color:#efe; font-weight:bold;'>Logged in:</span> {st.session_state['user_role'].title()}",
            unsafe_allow_html=True
        ) 
        st.markdown("---")
        current_time = datetime.now().strftime("%H:%M:%S")
        st.sidebar.markdown(f"⏱️ {current_time}")

        today = date.today()
        formatted_date = today.strftime("%A, %B %d, %Y") 
        st.sidebar.markdown(f"**{formatted_date}**")

    st.markdown("---")
  
    st.markdown("**View**")
    page = st.selectbox("", ["Billing", "Analytics Dashboard", "Order History"])
    st.markdown("---")
    st.sidebar.markdown("### Info")

    with st.sidebar.expander("📋About"):
         st.markdown("""
    **Restaurant Billing System**  
    Developed by Madhavi, basing Streamlit as the main framework.-

    ### Features
    - **Billing:** Manage customer orders and generate bills efficiently.
    - **Analytics Dashboard:** Visualize sales trends and order history with charts.
    - **Order History:** Review past orders with details and statuses.

    ### Contact
    For any questions or feedback, please reach out:  
    thotamadhavi107@gmail.com

    — Thank you for trying out this project!
    """)
    
    st.markdown("---")
    if st.button("Logout"):
        st.session_state["login_success"] = False
        st.rerun()

# --- BILLING PAGE ---
# --- Discounts and Coupons Logic ---

from datetime import datetime

COUPON_CODES = {
    "welcome10": 10,   # First-time customer only
    "festive5": 5,   # Open offer
    "newyear10": 10,
    "maincourse5": 5, #for main courses over 3+
    "combodesserts3": 3, #for desserts over 3+
}

def is_first_time_customer(phone):
    # TODO: 
    if phone and phone[-1].isdigit():
        return int(phone[-1]) % 2 == 0
    return False

def get_discount_percent(items, subtotal, payment_method, customer_phone, coupon_code):
    # Base discount by bill slab
    if subtotal > 5000:
        base_discount = 3
    elif subtotal > 2000:
        base_discount = 2
    else:
        base_discount = 0

    # Loyalty/first-time discount
    loyalty_discount = 2 if is_first_time_customer(customer_phone) else 0

    # Payment method discount
    payment_discount = 2 if payment_method.lower() in ["upi", "card"] else 0

    # Combo discounts
    dessert_count = sum(i['qty'] for i in items if i.get('category','').lower() == 'dessert')
    main_course_count = sum(i['qty'] for i in items if i.get('category','').lower() == 'main course')

    combo_discount = 0
    if dessert_count >= 3:
        combo_discount += 3
    if main_course_count >= 4:
        combo_discount += 5

    # Coupon discount (enforce welcome20 only for new)
    coupon_discount = COUPON_CODES.get(coupon_code.lower(), 0) if coupon_code else 0
    if coupon_code and coupon_code.lower() == "welcome20" and not is_first_time_customer(customer_phone):
        coupon_discount = 0

    total_discount = base_discount + loyalty_discount + payment_discount + combo_discount + coupon_discount
    return min(total_discount, 25)

def calculate_gst(items, discount_percent):
    total_gst = 0
    for item in items:
        discounted_price = item['price'] * (1 - discount_percent / 100)
        # Apply GST: 12% for main course, 5% others
        rate = 12 if item.get('category','').lower() == 'main course' else 5
        gst_item = discounted_price * item['qty'] * rate / 100
        total_gst += gst_item
    return total_gst


 #main billing logic

if page == "Billing":
    if "order_items" not in st.session_state:
        st.session_state["order_items"] = []

    st.title("Restaurant Billing System (Streamlit Web)")

    st.header("Menu")
    menu_df = pd.DataFrame(menu_data)
    menu_df['Quantity'] = 1

    selected = st.multiselect("Select menu items:", menu_df['name'])
    menu_selection = menu_df[menu_df['name'].isin(selected)]

    quantities = {}
    for idx, row in menu_selection.iterrows():
        qty = st.number_input(f"Qty for {row['name']}", min_value=1, value=1, key=f"qty_{row['id']}")
        quantities[row['id']] = qty

    if st.button("Add Selected to Order"):
        for idx, row in menu_selection.iterrows():
            item = {
                'menu_id': row['id'],
                'name': row['name'],
                'qty': quantities[row['id']],
                'price': row['price'],
                'gst': row['gst'],
                'category': row['category'],
            }
            # Check if already in cart, update qty
            found = False
            for oi in st.session_state["order_items"]:
                if oi['name'] == item['name']:
                    oi['qty'] += item['qty']
                    found = True
                    break
            if not found:
                st.session_state["order_items"].append(item)
        st.success("Items added to order.")

    st.subheader("Order Items")
    if st.session_state["order_items"]:
        st.write(pd.DataFrame(st.session_state["order_items"]))

    # --- Mode, Table and Payment Method Selection ---
    st.subheader("Order Info")
    mode = st.selectbox("Mode", ["Dine-In", "Takeaway"])
    if mode == "Dine-In":
        table = st.selectbox("Table", [f"Table {i}" for i in range(1, 11)])
    else:
        table = "N/A"
    payment_method = st.selectbox("Payment Method", ["Cash", "UPI", "Card"])

    # Customer Details
    st.subheader("Customer Details")
    customer_name = st.text_input("Customer Name")
    customer_phone = st.text_input("Phone Number")

    # Coupon Code
    coupon_options = [""] + list(COUPON_CODES.keys())  # Add empty for no coupon
    coupon_code = st.selectbox("Select Coupon Code (or leave blank):", coupon_options)


    # Bill display
    # --- HORIZONTAL ACTION BUTTONS ---
    st.markdown("""
    <style>
    /* Make columns only as wide as their content */
    div[data-testid="column"] {
       width: fit-content !important;
       flex: unset !important;
       padding: 0 4px !important;
    }

    /* Make buttons the same min width and fill their column */
    div[data-testid="column"] button {
       min-width: 140px !important;  /* Adjust this as needed */
       width: 100% !important;
       padding: 8px 0 !important;
       font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)


    col1, col2, col3, col4 = st.columns(4)

    with col1:
        preview_clicked = st.button("Preview Bill")
    with col2:
        save_clicked = st.button("Save Order")
    with col3:
        share_clicked = st.button("Share Bill")
    with col4:
        print_clicked = st.button("Print Bill")
  
    # Initialize toggle state for the share button
    if "share_toggle" not in st.session_state:
      st.session_state["share_toggle"] = False

  # --- LOGIC FOR EACH BUTTON ---

  # 1. Preview Bill Logic
    if preview_clicked:
       items = st.session_state["order_items"]
       if not items:
            st.warning("Add some items first!")
       elif not customer_name or not customer_phone:
            st.warning("Enter customer details!")
       else:
        subtotal = sum(i['qty'] * i['price'] for i in items)
        discount_percent = get_discount_percent(items, subtotal, payment_method, customer_phone, coupon_code)
        discount_amount = subtotal * discount_percent / 100
        subtotal_after_discount = subtotal - discount_amount
        gst_val = calculate_gst(items, discount_percent)
        total = subtotal_after_discount + gst_val

        st.text(f"Customer: {customer_name}\nPhone: {customer_phone}")
        st.text(f"Mode: {mode}\nTable: {table}\nPayment: {payment_method}")
        st.dataframe(pd.DataFrame(items))
        st.markdown(f"**Subtotal:** ₹{subtotal:.2f}")
        st.markdown(f"**Discount ({discount_percent}%):** -₹{discount_amount:.2f}")
        st.markdown(f"**Subtotal after Discount:** ₹{subtotal_after_discount:.2f}")
        st.markdown(f"**GST:** ₹{gst_val:.2f}")
        st.markdown(f"**Total:** ₹{total:.2f}")
        if items and customer_name and customer_phone:
       # Prepare bill data as DataFrame for CSV
          df = pd.DataFrame(items)
          df["total_price"] = df["qty"] * df["price"]

          csv_buffer = io.StringIO()
          df.to_csv(csv_buffer, index=False)
          csv_data = csv_buffer.getvalue()

         # Prepare bill data as JSON
          json_data = json.dumps(items, indent=4)

         # Download buttons below the bill
          st.download_button(
              label="Download Bill as CSV",
              data=csv_data,
              file_name="bill.csv",
              mime="text/csv"
            )

          st.download_button(
              label="Download Bill as JSON",
              data=json_data,
              file_name="bill.json",
              mime="application/json"
            )

     # 2. Finalize and Save Order Logic
    if save_clicked:
       items = st.session_state["order_items"]
       if not items:
            st.warning("Add some items first!")
       elif not customer_name or not customer_phone:
             st.warning("Enter customer details!")
       else:
            subtotal = sum(i['qty'] * i['price'] for i in items)
            discount_percent = get_discount_percent(items, subtotal, payment_method, customer_phone, coupon_code)
            discount_amount = subtotal * discount_percent / 100
            subtotal_after_discount = subtotal - discount_amount
            gst_val = calculate_gst(items, discount_percent)
            total = subtotal_after_discount + gst_val

            order_id = save_order(mode, payment_method, items, total, discount_percent, coupon_code, gst_val, customer_name, customer_phone)
            st.success(f"Order #{order_id} saved!")
            st.session_state["order_items"] = []

# 3. Share Bill Logic (toggles visibility of links)
 
# Only show share UI if there's a finished bill
    if st.session_state.get("share_toggle", False):
        st.markdown("---")
        message = (
            f"Customer: {customer_name}\n"
            f"Phone: {customer_phone}\n"
            f"Mode: {mode}\n"
            f"Table: {table}\n"
            f"Payment: {payment_method}\n"
            f"Subtotal: ₹{subtotal:.2f}\n"
            f"Discount ({discount_percent}%): -₹{discount_amount:.2f}\n"
            f"Subtotal after Discount: ₹{subtotal_after_discount:.2f}\n"
            f"GST: ₹{gst_val:.2f}\n"
            f"Total: ₹{total:.2f}\n"
        )
        items_str = "Items:\n"
        for item in items:
            items_str += f"- {item.get('name', '')} x{item.get('qty', 1)} @ ₹{item.get('price', 0)}\n"
        message += "\n" + items_str

        encoded_message = quote(message)
        mailto_link = f"mailto:?subject=Your Restaurant Bill&body={encoded_message}"
        whatsapp_url = f"https://wa.me/?text={encoded_message}"

        share_option = st.selectbox(
           "Choose sharing method:",
            ("Select...", "Share via Email", "Share via WhatsApp"),
        key="share_method"
        )

        if share_option == "Share via Email":
            st.markdown(
                f'<a href="{mailto_link}" target="_blank">📧 Click here to share via Email</a>', 
                unsafe_allow_html=True
            )
        elif share_option == "Share via WhatsApp":
            st.markdown(
                f'<a href="{whatsapp_url}" target="_blank">💬 Click here to share via WhatsApp</a>', 
                unsafe_allow_html=True
            )

    # 4. Print Bill Logic
    if print_clicked:
    # This will popup print dialog for the whole browser page
       components.html(
        """
        <script>
        window.print();
        </script>
        """,
        height=0,
    )

# --- ANALYTICS PAGE ---
elif page == "Analytics Dashboard":
    st.title("📊 Analytics Dashboard")

    orders = fetch_orders()
    order_cols = ['id', 'timestamp', 'mode', 'payment_method', 'total', 'discount_percent', 'coupon_code', 'gst_amount', 'customer_name', 'customer_phone']
    df = pd.DataFrame(orders, columns=order_cols)

    conn = sqlite3.connect(DB_PATH)
    item_df = pd.read_sql_query("""SELECT oi.name, oi.quantity, oi.price, oi.gst, m.category
                                   FROM order_items oi
                                   LEFT JOIN menu m ON oi.menu_id = m.id""", conn)
    conn.close()

    # 1. Top Selling Items
    st.subheader("🍔 Top Selling Items (by quantity)")
    top_items = item_df.groupby("name")["quantity"].sum().sort_values(ascending=False).head(10)
    st.bar_chart(top_items)

    # 2. Top Desserts
    if "Dessert" in item_df['category'].unique():
        st.subheader("🍨 Top Desserts (by quantity)")
        dessert_df = item_df[item_df["category"] == "Dessert"]
        top_desserts = dessert_df.groupby("name")["quantity"].sum().sort_values(ascending=False)
        st.bar_chart(top_desserts)
    else:
        st.info("No dessert category available in your menu data.")

    # 3. Revenue by Payment Method
    st.subheader("💳 Revenue by Payment Method")
    pay_df = df.groupby("payment_method")["total"].sum()
    st.bar_chart(pay_df)

    # 4. Sales Trend by Day
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    st.subheader("Revenue Trend")

    trend_option = st.selectbox("Select Revenue Trend:", ["Daily", "Hourly"])

    if trend_option == "Daily":
       trend_df = df.resample("D", on="timestamp")["total"].sum()
       st.line_chart(trend_df)
    else:
        last_week_df = df[df["timestamp"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        hourly_trend_df = last_week_df.resample("H", on="timestamp")["total"].sum()
        st.line_chart(hourly_trend_df)
# --- ORDER HISTORY PAGE ---

elif page == "Order History":
    # Order History table at top
    st.title("📜 Order History")

# Fetch and display the full order table
    orders = fetch_orders()
    df = pd.DataFrame(
         orders,
         columns=["id", "timestamp", "mode", "payment_method", "total",
             "discount_percent", "coupon_code", "gst_amount",
             "customer_name", "customer_phone"]
     )
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    st.dataframe(df)
      
    st.markdown("---")
    summary_period = st.selectbox("Select Summary Period", ["Daily", "Weekly", "Monthly"])

# --- Compute filtered summary ---
    now = pd.Timestamp.now()
    if summary_period == "Daily":
        start_date = now.normalize()
    elif summary_period == "Weekly":
         start_date = now - pd.Timedelta(days=now.weekday())
         start_date = start_date.normalize()
    elif summary_period == "Monthly":
         start_date = now.replace(day=1).normalize()
    filtered_df = df[df['timestamp'] >= start_date]

# --- Display summary table ---
    st.markdown("---")
    st.subheader(f"{summary_period} Sales Summary")
    st.dataframe(filtered_df)

# --- Download button, as a single wide row/button ---
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.download_button(
        label=f"Download {summary_period} Sales Report as CSV",
        data=filtered_df.to_csv(index=False),
        file_name=f"sales_report_{summary_period.lower()}.csv",
        mime="text/csv"
        )
# python3 -m streamlit run ui/main_ui.py