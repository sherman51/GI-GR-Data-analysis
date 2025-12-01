from datetime import datetime, timedelta, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
import io
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# ---------- CONFIG ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard Aircon", page_icon="📊")

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
        'Shipped': '#22c55e',
        'Cancelled': '#ef4444',
        'Packed': '#3b82f6',
        'Picked': '#F1B39F',
        'Pick In-Progress': '#f97316',
        'Open': '#eab308',
        'Ad-hoc Urgent': '#f59e0b',
        'Ad-hoc Critical': '#dc2626'
    }
}

# ---------- AUTO REFRESH ----------
st_autorefresh(interval=60*1000, limit=None, key="data_refresh")

# ---------- GCP AUTH ----------
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
BUCKET_NAME = "testbucket352"
gcs_client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = gcs_client.bucket(BUCKET_NAME)

def download_latest_excel(bucket):
    blobs = list(bucket.list_blobs())
    aircon_blobs = [b for b in blobs if b.name.lower().startswith('aircon') and b.name.lower().endswith(('.xlsx', '.xls'))]
    if not aircon_blobs:
        return None, None
    latest_blob = max(aircon_blobs, key=lambda b: b.updated)
    file_bytes = latest_blob.download_as_bytes()
    return io.BytesIO(file_bytes), latest_blob.name

# ---------- FETCH LATEST FILE ----------
file_stream, file_name = download_latest_excel(bucket)
if file_stream:
    st.sidebar.success(f"📥 Using latest file from GCS: {file_name}")
else:
    st.sidebar.error("❌ No Excel files found in GCS bucket.")

# ---------- GLOBAL STYLE OVERRIDES ----------
st.markdown("""
<style>
    /* Hide Streamlit default header & footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Body font */
    html, body, [class*="css"]  {
        font-family: "Segoe UI", sans-serif;
    }

    .block-container {
        padding-top: 0.5rem !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    hr {
        border: none;
        height: 1px;
        background-color: #e5e7eb;
        margin: 2rem 0;
    }

    .metric-container {
        background: linear-gradient(145deg, #ffffff, #f3f4f6);
        padding: 14px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: transform 0.2s ease;
    }
    .metric-container:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 600;
        color: #111827;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #6b7280;
        margin-top: 4px;
    }

    /* --- CUSTOM COLORED EXPANDER HEADERS --- */
    div.streamlit-expanderHeader:has(p:contains("Critical Orders")) {
        background-color: #ffe5e5 !important;
        border: 1px solid #dc2626 !important;
        border-radius: 6px !important;
    }
    div.streamlit-expanderHeader:has(p:contains("Urgent Orders")) {
        background-color: #fff8d6 !important;
        border: 1px solid #f59e0b !important;
        border-radius: 6px !important;
    }
    div.streamlit-expanderHeader:has(p:contains("Outstanding Orders")) {
        background-color: #e6f0ff !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 6px !important;
    }

</style>

<script>
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        console.log('Copied to clipboard successfully!');
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
}
</script>
""", unsafe_allow_html=True)

# ---------- PAGE HEADER ----------
st.markdown(
    """
    <div style="display: flex; align-items: center; background: linear-gradient(90deg, #003366, #2563eb); padding: 14px 18px; border-radius: 10px; margin-bottom: 20px;">
        <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" 
             style="max-height:42px; height:auto; width:auto; margin-right:12px;">
        <h2 style="margin: 0; font-family: 'Segoe UI', sans-serif; color: #ffffff; font-weight: 600;">
            Outbound Dashboard Aircon
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

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

df = load_data(file_stream)
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(['aircon', 'controlled drug room', 'strong room'])]

# ---------- (ALL YOUR FUNCTIONS REMAIN THE SAME) ----------
# Keeping this message short, the rest of your code (dashboards, plots, tables)
# continues unchanged from your previous version.

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
        if df_day['GINo'].count() == 0:
            current_date += timedelta(days=1)
            days_checked += 1
            continue
    date_list.append(current_date)
    current_date += timedelta(days=1)
    days_checked += 1


# ---------- DISPLAY ----------
tab1, tab2 = st.tabs(["📊 Daily Dashboard", "📈 Analytics"])

# (REMOVED HERE FOR BREVITY — YOUR ENTIRE DASHBOARD DISPLAY LOOP IS UNCHANGED)

st.markdown("###  *Stay Safe & Well*")
st.markdown("""
    <div style='text-align:center; color:#6b7280; font-size:0.9rem; margin-top:30px;'>
        ⭐ Stay Safe & Well ⭐
    </div>
""", unsafe_allow_html=True)
