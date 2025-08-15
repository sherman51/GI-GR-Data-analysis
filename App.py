from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
import io

# ---------- CONFIG ----------
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
    "status_segments": ['Open','Pick In-Progress', 'Picked', 'Packed', 'Shipped', 'Cancelled'],
    "colors": {
        'Shipped': 'green',
        'Cancelled': 'red',
        'Packed': 'blue',
        'Picked': 'yellow',
        'Pick In-Progress': 'orange',
        'Open': 'salmon',
        'Ad-hoc Urgent': 'orange',
        'Ad-hoc Critical': 'crimson'
    }
}

# ---------- GCP AUTH ----------
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
BUCKET_NAME = "testbucket352"

# Initialize GCS client
gcs_client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = gcs_client.bucket(BUCKET_NAME)

def download_latest_excel(bucket):
    blobs = list(bucket.list_blobs())
    excel_blobs = [b for b in blobs if b.name.lower().endswith(('.xlsx', '.xls'))]
    if not excel_blobs:
        return None, None
    latest_blob = max(excel_blobs, key=lambda b: b.updated)
    file_bytes = latest_blob.download_as_bytes()
    return io.BytesIO(file_bytes), latest_blob.name

# Auto-refresh every 60 sec
st_autorefresh = st.experimental_rerun  # Placeholder in case needed
st_autorefresh_interval = 60 * 1000
st_autorefresh_key = "data_refresh"
st_autorefresh_enabled = st.experimental_data_editor  # Not used here; for structure

# ---------- FETCH LATEST FILE ----------
file_stream, file_name = download_latest_excel(bucket)
if file_stream:
    st.sidebar.success(f"📥 Using latest file from GCS: {file_name}")
else:
    st.sidebar.error("❌ No Excel files found in GCS bucket.")
    st.stop()

# ---------- PAGE HEADER ----------
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

st.markdown("""
<style>
hr { border: none; height: 1px; background-color: #d3d3d3; margin: 2rem 0; }
.metric-container {
    background-color: #f4f4f4;
    padding: 12px;
    border-radius: 8px;
    text-align: center;
}
.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
}
.metric-label {
    font-size: 0.9rem;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# ---------- HELPER FUNCTIONS ----------
def load_data(file):
    try:
        df = pd.read_excel(file, skiprows=6, engine='openpyxl')
    except Exception:
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

# Load data from latest GCS file
df = load_data(file_stream)

# ---------- FILTER AIRCON ----------
aircon_zones = ['aircon', 'controlled drug room', 'strong room']
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)]

# ---------- DASHBOARD FUNCTIONS ----------
# (Keep all your daily_overview, daily_completed_pie, etc. functions exactly the same)

# Paste all your existing functions here (unchanged)...
# daily_overview(...)
# daily_completed_pie(...)
# order_status_matrix(...)
# adhoc_orders_section(...)
# expiry_date_summary(...)
# order_volume_summary(...)
# performance_metrics(...)

# ---------- DATE LOGIC ----------
date_list = []
days_checked = 0
current_date = datetime.today().date()

while len(date_list) < 3 and days_checked < 7:
    weekday = current_date.weekday()
    if weekday == 6:
        current_date += timedelta(days=1)
        days_checked += 1
        continue
    if weekday == 5:
        df_day = df[df['ExpDate'].dt.date == current_date]
        if df_day.empty:
            current_date += timedelta(days=2)
            days_checked += 2
            continue
    date_list.append(current_date)
    current_date += timedelta(days=1)
    days_checked += 1

# ---------- DISPLAY ----------
layout = []
for i in range(len(date_list)):
    layout.append(5)
    if i != len(date_list) - 1:
        layout.append(0.5)
cols = st.columns(layout)

col_index = 0
for i, dash_date in enumerate(date_list):
    with cols[col_index]:
        df_day = df[df['ExpDate'].dt.date == dash_date]

        st.markdown(
            f"<h5 style='text-align:center; color:gray;'>{dash_date.strftime('%d %b %Y')}</h5>",
            unsafe_allow_html=True
        )
        st.markdown("##### 🚨 Urgent and Critical")
        adhoc_orders_section(df_day, key_prefix=f"day{i}")
        st.markdown("##### ✅ % completion")
        daily_completed_pie(df_day, key_prefix=f"day{i"])
        st.markdown("##### 📋 Order Status Table")
        order_status_matrix(df_day, key_prefix=f"day{i}")
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("##### 📦 Orders breakdown")
        daily_overview(df_day, key_prefix=f"day{i}")

    if i != len(date_list) - 1:
        with cols[col_index + 1]:
            st.markdown(
            """
            <div style='height: 135vh; border-left: 2px solid #888; margin: auto;'></div>
            """,
            unsafe_allow_html=True
        )
    col_index += 2

# ---------- BOTTOM SECTION ----------
col1, col2 = st.columns(2)
with col1:
    st.markdown("### 📊 Order lines (Past 14 Days)")
    order_volume_summary(df, key_prefix="overall")
    expiry_date_summary(df, key_prefix="overall")
with col2:
    st.markdown("### 📈 Performance Metrics")
    performance_metrics(df, key_prefix="overall")

st.markdown("###  *Stay Safe & Well*")
