from datetime import datetime, timedelta, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
import io
from streamlit_autorefresh import st_autorefresh

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
        'Shipped': '#28a745',
        'Cancelled': '#dc3545',
        'Packed': '#007bff',
        'Picked': '#ffc107',
        'Pick In-Progress': '#fd7e14',
        'Open': '#6c757d',
        'Ad-hoc Urgent': '#ffb84d',
        'Ad-hoc Critical': '#e63946'
    }
}

# ---------- AUTO REFRESH ----------
st_autorefresh(interval=300*1000, limit=None, key="data_refresh")

# ---------- GCP AUTH ----------
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
BUCKET_NAME = "testbucket352"
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

# ---------- FETCH LATEST FILE ----------
file_stream, file_name = download_latest_excel(bucket)
if file_stream:
    st.sidebar.success(f"📥 Using latest file from GCS: {file_name}")
else:
    st.sidebar.error("❌ No Excel files found in GCS bucket.")

# ---------- GLOBAL STYLING ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    .block-container { padding-top: 0rem !important; }
    header {visibility: hidden;}
    body, h1, h2, h3, h4, h5, h6, p, div { font-family: 'Inter', sans-serif; }
    hr { border: none; height: 2px; background: linear-gradient(to right, #eee, #bbb, #eee); margin: 2rem 0; }
    .metric-container { background-color: #ffffff; padding: 16px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #212529; }
    .metric-label { font-size: 0.9rem; color: #6c757d; }
    .dataframe td:hover { background-color: #f1f3f5 !important; transition: background 0.2s ease-in-out; }
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
<div style="display: flex; align-items: center; background-color: #003366; padding: 14px 18px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
    <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" style="max-height:40px; height:auto; width:auto; margin-right:12px;">
    <h3 style="margin: 0; font-family: 'Inter', sans-serif; font-weight:600; color: #ffffff;">📊 Outbound Dashboard Aircon</h3>
</div>
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

# Load data
df = load_data(file_stream)
aircon_zones = ['aircon', 'controlled drug room', 'strong room']
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)]

# ---------- CHART THEME ----------
def apply_plotly_theme(fig):
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=12, color="#333"),
        margin=dict(l=10, r=10, t=40, b=20)
    )
    return fig

# ---------- DASHBOARD FUNCTIONS ----------
def daily_overview(df):
    today = date.today()
    df_today = df[df['ExpDate'].dt.date == today]
    count = df_today.shape[0]
    st.markdown("<div class='metric-container'><div class='metric-value'>{}</div><div class='metric-label'>Orders Today</div></div>".format(count), unsafe_allow_html=True)

def daily_completed_pie(df):
    today = date.today()
    df_today = df[df['ExpDate'].dt.date == today]
    status_counts = df_today['Order Status'].value_counts()
    fig = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=.4)])
    fig = apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

def order_status_matrix(df):
    pivot = pd.pivot_table(df, values='Order', index='Order Type', columns='Order Status', aggfunc='count', fill_value=0)
    st.dataframe(pivot, use_container_width=True)

def adhoc_orders_section(df):
    adhoc_df = df[df['Order Type'].str.contains("Ad-hoc")]
    st.write("### Ad-hoc Orders")
    st.dataframe(adhoc_df[['Order', 'Order Type', 'Order Status', 'ExpDate']], use_container_width=True)

def expiry_date_summary(df):
    exp_summary = df.groupby(df['ExpDate'].dt.date).size().reset_index(name='Orders')
    fig = go.Figure([go.Bar(x=exp_summary['ExpDate'], y=exp_summary['Orders'])])
    fig = apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

def order_volume_summary(df):
    vol_summary = df.groupby('Order Type').size().reset_index(name='Orders')
    fig = go.Figure([go.Bar(x=vol_summary['Order Type'], y=vol_summary['Orders'])])
    fig = apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

def performance_metrics(df):
    shipped = df[df['Order Status'] == 'Shipped'].shape[0]
    cancelled = df[df['Order Status'] == 'Cancelled'].shape[0]
    st.markdown("<div class='metric-container'><div class='metric-value'>{}</div><div class='metric-label'>Shipped</div></div>".format(shipped), unsafe_allow_html=True)
    st.markdown("<div class='metric-container'><div class='metric-value'>{}</div><div class='metric-label'>Cancelled</div></div>".format(cancelled), unsafe_allow_html=True)

# ---------- RENDER SECTIONS ----------
st.title("Daily Outbound Overview")
daily_overview(df)
daily_completed_pie(df)
order_status_matrix(df)
adhoc_orders_section(df)
expiry_date_summary(df)
order_volume_summary(df)
performance_metrics(df)

# ---------- FOOTER ----------
st.markdown("""<div style="text-align:center; margin-top:2rem; color:#6c757d; font-size:0.9rem;">✨ Stay Safe & Well ✨</div>""", unsafe_allow_html=True)
