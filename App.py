from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
from io import BytesIO

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Outbound Dashboard Aircon")

CONFIG = {
    "priority_map": {
        '1-Normal': 'normal',
        '2-ADHOC Normal': 'Ad-hoc Normal',
        '3-ADHOC Urgent': 'Ad-hoc Urgent',
        '4-ADHOC Critical': 'Ad-hoc Critical'
    },
    "status_map": {
        '10-Open': 'Open',
        '15-Processing': 'Open',
        '20-Partially Allocated': 'Open',
        '25-Fully Allocated': 'Pick In-Progress',
        '35-Pick in Progress': 'Pick In-Progress',
        '45-Picked': 'Picked',
        '65-Packed': 'Packed',
        '75-Shipped': 'Shipped',
        '98-Cancelled': 'Cancelled'
    },
    "order_types": ['Back Orders', 'normal', 'Ad-hoc Normal', 'Ad-hoc Urgent', 'Ad-hoc Critical'],
    "status_segments": ['Open', 'Pick In-Progress', 'Picked', 'Packed', 'Shipped', 'Cancelled'],
    "colors": {
        'Shipped': 'green',
        'Cancelled': 'red',
        'Packed': 'blue',
        'Picked': 'yellow',
        'Pick In-Progress': 'Orange',
        'Open': 'salmon',
        'Ad-hoc Urgent': 'orange',
        'Ad-hoc Critical': 'crimson'
    }
}

# --- GOOGLE CLOUD STORAGE AUTHENTICATION ---
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket_name = "testbucket352"  # Change to your bucket name
bucket = client.bucket(bucket_name)

# --- DATA LOADING FUNCTIONS ---
def load_data(file):
    try:
        df = pd.read_excel(file, skiprows=6, engine='openpyxl')
    except Exception as e:
        st.error("❌ Failed to read Excel file. Make sure it's a valid .xlsx file.")
        st.stop()

    df.columns = df.columns.str.strip()
    df.dropna(axis=1, how="all", inplace=True)
    df.dropna(how="all", inplace=True)

    for col in ['ExpDate', 'CreatedOn', 'ShippedOn']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    df = df[df['ExpDate'].notna()]
    df['Order Type'] = df['Priority'].map(CONFIG['priority_map']).fillna(df['Priority'])
    df['Status'] = df['Status'].astype(str).str.strip()
    df['Order Status'] = df['Status'].map(CONFIG['status_map']).fillna('Open')

    return df

def load_data_from_gcs(blob_name):
    blob = bucket.blob(blob_name)
    if not blob.exists():
        st.error(f"File '{blob_name}' does not exist in bucket '{bucket_name}'.")
        st.stop()
    data_bytes = blob.download_as_bytes()
    excel_io = BytesIO(data_bytes)
    return load_data(excel_io)

# --- DASHBOARD HELPER FUNCTIONS ---
def adhoc_orders_section(df_day, key_prefix):
    adhoc = df_day[df_day['Order Type'].isin(['Ad-hoc Urgent', 'Ad-hoc Critical'])]
    if adhoc.empty:
        st.info("No Urgent or Critical orders today.")
        return
    counts = adhoc['Order Type'].value_counts()
    for order_type in ['Ad-hoc Critical', 'Ad-hoc Urgent']:
        count = counts.get(order_type, 0)
        color = CONFIG['colors'].get(order_type, 'black')
        st.markdown(f"<b style='color:{color}'>{order_type}: {count}</b>", unsafe_allow_html=True)

def daily_completed_pie(df_day, key_prefix):
    status_counts = df_day['Order Status'].value_counts()
    labels = []
    values = []
    colors = []
    for status in CONFIG['status_segments']:
        if status in status_counts:
            labels.append(status)
            values.append(status_counts[status])
            colors.append(CONFIG['colors'].get(status, 'gray'))

    if not values:
        st.info("No orders for completion pie.")
        return

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=colors, hole=.4)])
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
    st.plotly_chart(fig, use_container_width=True)

def order_status_matrix(df_day, key_prefix):
    if df_day.empty:
        st.info("No orders to display in Order Status Table.")
        return
    # Pivot table of counts by Order Type and Status
    pivot = pd.pivot_table(
        df_day,
        index='Order Type',
        columns='Order Status',
        values='Order Number',
        aggfunc='count',
        fill_value=0
    ).reindex(index=CONFIG['order_types'], columns=CONFIG['status_segments'], fill_value=0)

    st.dataframe(pivot.style.background_gradient(cmap='Blues'))

def daily_overview(df_day, key_prefix):
    if df_day.empty:
        st.info("No orders to display in daily overview.")
        return
    order_type_counts = df_day['Order Type'].value_counts()
    for ot in CONFIG['order_types']:
        count = order_type_counts.get(ot, 0)
        color = CONFIG['colors'].get(ot, 'black')
        st.markdown(f"<b style='color:{color}'>{ot}: {count}</b>", unsafe_allow_html=True)

def order_volume_summary(df, key_prefix):
    last_14_days = datetime.today().date() - timedelta(days=14)
    df_14 = df[df['ExpDate'].dt.date >= last_14_days]
    if df_14.empty:
        st.info("No order data for past 14 days.")
        return
    daily_counts = df_14.groupby(df_14['ExpDate'].dt.date).size()
    fig = go.Figure(data=[go.Bar(x=daily_counts.index, y=daily_counts.values, marker_color='royalblue')])
    fig.update_layout(title='Order Lines (Past 14 Days)', xaxis_title='Date', yaxis_title='Orders', height=300)
    st.plotly_chart(fig, use_container_width=True)

def expiry_date_summary(df, key_prefix):
    exp_counts = df['ExpDate'].dt.date.value_counts().sort_index()
    fig = go.Figure(data=[go.Scatter(x=exp_counts.index, y=exp_counts.values, mode='lines+markers', line=dict(color='orange'))])
    fig.update_layout(title='Expiry Date Summary', xaxis_title='Expiry Date', yaxis_title='Orders', height=300)
    st.plotly_chart(fig, use_container_width=True)

def performance_metrics(df, key_prefix):
    shipped = df[df['Order Status'] == 'Shipped']
    packed = df[df['Order Status'] == 'Packed']
    total_orders = len(df)
    shipped_pct = (len(shipped) / total_orders) * 100 if total_orders else 0
    packed_pct = (len(packed) / total_orders) * 100 if total_orders else 0
    st.metric("Orders Shipped %", f"{shipped_pct:.1f}%")
    st.metric("Orders Packed %", f"{packed_pct:.1f}%")

# --- MAIN APP ---
st.markdown(
    """
    <div style="display: flex; align-items: center; background-color: #003366; padding: 12px 16px; border-radius: 6px;">
        <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" 
             style="max-height:40px; height:auto; width:auto; margin-right:10px;">
        <h3 style="margin: 0; font-family: Arial, sans-serif; color: #ffffff;">
            - <b>Outbound Dashboard Aircon</b>
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

# List Excel files in GCS folder Aircon/
prefix = "Aircon/"
blobs = list(bucket.list_blobs(prefix=prefix))
excel_files = [blob.name for blob in blobs if blob.name.endswith((".xls", ".xlsx"))]

if not excel_files:
    st.warning(f"No Excel files found in '{prefix}' folder in bucket '{bucket_name}'.")
    st.stop()

selected_file = st.sidebar.selectbox("Select Excel file from GCS", excel_files)
if selected_file:
    df = load_data_from_gcs(selected_file)
    st.success(f"Loaded data from {selected_file}")
else:
    st.info("Please select an Excel file from the list.")


if 'df' in locals():
    # Filter only aircon related zones (case insensitive)
    aircon_zones = ['aircon', 'controlled drug room', 'strong room']
    df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)]

    # Smart date list logic (same as your original)
    date_list = []
    days_checked = 0
    current_date = datetime.today().date()

    while len(date_list) < 3 and days_checked < 7:
        weekday = current_date.weekday()
        if weekday == 6:  # Sunday skip
            current_date += timedelta(days=1)
            days_checked += 1
            continue
        if weekday == 5:  # Saturday special check
            df_day = df[df['ExpDate'].dt.date == current_date]
            if df_day.empty:
                current_date += timedelta(days=2)
                days_checked += 2
                continue
        date_list.append(current_date)
        current_date += timedelta(days=1)
        days_checked += 1

    cols = st.columns(len(date_list)*2 - 1)
    for i, dash_date in enumerate(date_list):
        with cols[i*2]:
            df_day = df[df['ExpDate'].dt.date == dash_date]
            st.markdown(f"<h5 style='text-align:center; color:gray;'>{dash_date.strftime('%d %b %Y')}</h5>", unsafe_allow_html=True)

            st.markdown("##### 🚨 Urgent and Critical")
            adhoc_orders_section(df_day, key_prefix=f"day{i}")

            st.markdown("##### ✅ % completion")
            daily_completed_pie(df_day, key_prefix=f"day{i}")

            st.markdown("##### 📋 Order Status Table")
            order_status_matrix(df_day, key_prefix=f"day{i}")

            st.markdown("<hr>", unsafe_allow_html=True)

            st.markdown("##### 📦 Orders breakdown")
            daily_overview(df_day, key_prefix=f"day{i}")

        if i != len(date_list) - 1:
            with cols[i*2 + 1]:
                st.markdown("<div style='height: 135vh; border-left: 2px solid #888; margin: auto;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Order lines (Past 14 Days)")
        order_volume_summary(df, key_prefix="overall")
        expiry_date_summary(df, key_prefix="overall")

    with col2:
        st.markdown("### 📈 Performance Metrics")
        performance_metrics(df, key_prefix="overall")

    st.markdown("###  *Stay Safe & Well*")

