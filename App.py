import streamlit as st
import pandas as pd
import numpy as np
import datetime



uploaded_file = st.file_uploader("Choose an XLSX file", type=['xlsx'])



# Mock data generation
def generate_inventory_data():
    categories = ['Electronics', 'Furniture', 'Clothing', 'Groceries', 'Toys']
    data = {
        'Product': [f'Item {i}' for i in range(1, 11)],
        'Category': np.random.choice(categories, size=10),
        'Stock': np.random.randint(5, 100, size=10),
        'Price ($)': np.random.uniform(10, 500, size=10).round(2),
    }
    return pd.DataFrame(data)

def generate_order_data():
    status = ['Pending', 'Shipped', 'Delivered', 'Returned']
    data = {
        'Order ID': [f'O{1000 + i}' for i in range(1, 6)],
        'Customer': [f'Customer {i}' for i in range(1, 6)],
        'Status': np.random.choice(status, size=5),
        'Amount ($)': np.random.uniform(50, 300, size=5).round(2),
        'Order Date': [datetime.date.today() - datetime.timedelta(days=np.random.randint(1, 10)) for _ in range(5)],
    }
    return pd.DataFrame(data)

def generate_warehouse_activity():
    activities = ['Item Received', 'Item Picked', 'Order Packed', 'Order Shipped']
    data = {
        'Activity': np.random.choice(activities, size=10),
        'Timestamp': [datetime.datetime.now() - datetime.timedelta(minutes=np.random.randint(1, 60)) for _ in range(10)],
    }
    return pd.DataFrame(data)

# Streamlit UI
st.set_page_config(page_title="Warehouse Management Dashboard", page_icon=":package:", layout="wide")

# Header
st.title("Warehouse Management Dashboard")
st.markdown("This dashboard provides insights into your warehouse operations.")

# Sidebar for Navigation
st.sidebar.header("Navigation")
dashboard_option = st.sidebar.radio("Choose a view", ("Inventory Overview", "Order Status", "Warehouse Activity"))

# Main dashboard sections
if dashboard_option == "Inventory Overview":
    st.subheader("Inventory Overview")
    inventory_data = generate_inventory_data()
    st.dataframe(inventory_data)
    
    st.markdown("### Total Stock Value")
    total_stock_value = (inventory_data['Stock'] * inventory_data['Price ($)']).sum()
    st.metric("Total Value of Inventory", f"${total_stock_value:,.2f}")

elif dashboard_option == "Order Status":
    st.subheader("Order Status")
    order_data = generate_order_data()
    st.dataframe(order_data)

    # Order status breakdown
    st.markdown("### Order Status Breakdown")
    order_status_count = order_data['Status'].value_counts()
    st.bar_chart(order_status_count)

elif dashboard_option == "Warehouse Activity":
    st.subheader("Recent Warehouse Activity")
    activity_data = generate_warehouse_activity()
    st.dataframe(activity_data)
    
    st.markdown("### Recent Activities")
    st.write("This section shows the latest activities in the warehouse, such as receiving, packing, or shipping.")

    activity_status_count = activity_data['Activity'].value_counts()
    st.bar_chart(activity_status_count)

# Footer
st.markdown("""
    <br><hr>
    <footer>
        <p style="font-size: 12px; text-align: center;">
            Built with ❤️ by Your Team
        </p>
    </footer>
""", unsafe_allow_html=True)

