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
    st.stop()

# ---------- PAGE HEADER ----------
st.markdown("""
<style>
    .block-container {
        padding-top: 0rem !important;   /* remove white space above first element */
    }
    header {visibility: hidden;}       /* hide default streamlit header bar */
</style>
""", unsafe_allow_html=True)

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

# Load data
df = load_data(file_stream)

# Filter aircon zones
aircon_zones = ['aircon', 'controlled drug room', 'strong room']
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)]

# ---------- DASHBOARD FUNCTIONS ----------
# Daily overview
def daily_overview(df_today, key_prefix=""):
    total_order_lines = df_today.shape[0]
    unique_gino = df_today['GINo'].nunique()

    # --- Smaller metric cards ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div class='metric-container' style='padding:8px;'>"
            f"<div class='metric-value' style='font-size:1.1rem;'>{total_order_lines}</div>"
            f"<div class='metric-label' style='font-size:0.75rem;'>📦 Total Order Lines</div></div>",
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div class='metric-container' style='padding:8px;'>"
            f"<div class='metric-value' style='font-size:1.1rem;'>{unique_gino}</div>"
            f"<div class='metric-label' style='font-size:0.75rem;'>🔢 Total GINo</div></div>",
            unsafe_allow_html=True
        )

    # --- Stacked horizontal bar chart ---
    order_types = CONFIG['order_types']
    segments = CONFIG['status_segments']
    colors = CONFIG['colors']

    data = {seg: [] for seg in segments}
    for ot in order_types:
        ot_df = df_today[df_today['Order Type'] == ot]
        for seg in segments:
            count = (ot_df['Order Status'] == seg).sum()
            data[seg].append(count)

    # filter out order types with zero total
    filtered_order_types = []
    filtered_data = {seg: [] for seg in segments}
    for idx, ot in enumerate(order_types):
        total = sum(data[seg][idx] for seg in segments)
        if total > 0:
            filtered_order_types.append(ot)
            for seg in segments:
                filtered_data[seg].append(data[seg][idx])

    # build figure
    bar_fig = go.Figure()
    for seg in segments:
        bar_fig.add_trace(go.Bar(
            y=filtered_order_types,
            x=filtered_data[seg],
            name=seg,
            orientation='h',
            marker=dict(color=colors[seg]),
            # 🔴 Removed: width=1.0
        ))

    # layout improvements
    bar_fig.update_layout(
        barmode='stack',
        bargap=0,  # 🔥 remove vertical space between bars
        xaxis_title="Order Count",
        type = "log",
        margin=dict(l=10, r=10, t=20, b=20),
        height=40 * len(filtered_order_types) + 100,
        yaxis=dict(automargin=True)
    )


    st.plotly_chart(bar_fig, use_container_width=True, key=f"{key_prefix}_overview")


# Daily completed pie
def daily_completed_pie(df_today, key_prefix=""):
    total_orders = df_today.shape[0]
    completed_orders = df_today['Order Status'].isin(['Packed', 'Shipped']).sum()
    completed_pct = (completed_orders / total_orders * 100) if total_orders else 0
    fig = go.Figure(go.Pie(
        values=[completed_pct, 100 - completed_pct],
        labels=["Completed", "Outstanding"],
        marker_colors=['mediumseagreen', 'lightgray'],
        hole=0.6,
        textinfo='none',
        sort=False
    ))
    fig.update_layout(
        width=200,
        height=200,
        margin=dict(l=10, r=10, t=30, b=10),
        annotations=[dict(text=f"{completed_pct:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False)]
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_completed")

# Order status matrix
def order_status_matrix(df_today, key_prefix=""):
    df_status_table = df_today.groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)
    df_status_table = df_status_table.reindex(index=CONFIG['order_types'],
                                              columns=CONFIG['status_segments'],
                                              fill_value=0)
    st.dataframe(df_status_table, key=f"{key_prefix}_status")

# Ad-hoc orders
def adhoc_orders_section(df_today, key_prefix=""):
    not_completed_df = df_today[~df_today['Status'].isin(['Packed', 'Shipped'])]
    urgent_df = not_completed_df[not_completed_df['Order Type'] == 'Ad-hoc Urgent']
    critical_df = not_completed_df[not_completed_df['Order Type'] == 'Ad-hoc Critical']
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div style='background-color: #f8e5a1; padding:10px; border-radius:8px; text-align:center;'>⚠ Urgent Orders: {urgent_df['GINo'].nunique()}</div>", unsafe_allow_html=True)
        if not urgent_df.empty:
            st.dataframe(pd.DataFrame({"GI No": urgent_df['GINo'].unique()}), key=f"{key_prefix}_urgent")
    with col2:
        st.markdown(f"<div style='background-color: #f5a1a1; padding:10px; border-radius:8px; text-align:center;'>🚨 Critical Orders: {critical_df['GINo'].nunique()}</div>", unsafe_allow_html=True)
        if not critical_df.empty:
            st.dataframe(pd.DataFrame({"GI No": critical_df['GINo'].unique()}), key=f"{key_prefix}_critical")

# Expiry date summary
def expiry_date_summary(df, key_prefix=""):
    recent_df = df[df['ExpDate'] >= pd.Timestamp.today() - pd.Timedelta(days=14)]
    daily_summary = recent_df.groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
    cancelled_summary = recent_df[recent_df['Status'] == '98-Cancelled'] \
        .groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
    dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
    orders_received = [daily_summary.get(date, 0) for date in dates]
    orders_cancelled = [cancelled_summary.get(date, 0) for date in dates]
    fig = go.Figure(data=[
        go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='lightgreen'),
        go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='indianred')
    ])
    fig.update_layout(barmode='group', xaxis_title='Expiry Date', yaxis_title='Order Count')
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_expiry")

# Order volume summary
def order_volume_summary(df, key_prefix=""):
    today = pd.Timestamp.today().normalize()
    recent_df = df[(df['ExpDate'] >= today - pd.Timedelta(days=14)) & (df['ExpDate'] <= today)]
    daily_counts = recent_df.groupby(recent_df['ExpDate'].dt.date)['GINo'].count()
    if daily_counts.empty:
        st.info("No orders found for the past 14 days.")
        return
    peak_day_vol = daily_counts.max()
    avg_vol = daily_counts.mean()
    low_day_vol = daily_counts.min()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-container'><div class='metric-value'>{peak_day_vol}</div><div class='metric-label'>📈 Peak Day Volume</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-container'><div class='metric-value'>{avg_vol:.1f}</div><div class='metric-label'>📊 Average Daily Volume</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-container'><div class='metric-value'>{low_day_vol}</div><div class='metric-label'>📉 Lowest Day Volume</div></div>", unsafe_allow_html=True)

# Performance metrics
def performance_metrics(df, key_prefix=""):
    today = pd.Timestamp.today().normalize()
    recent_past_df = df[(df['ExpDate'] < today) & (df['ExpDate'] >= today - pd.Timedelta(days=14))]
    total_expected = recent_past_df['ExpectedQTY'].sum()
    total_shipped = recent_past_df['ShippedQTY'].sum()
    total_variance = recent_past_df['VarianceQTY'].sum()
    missed = total_expected - total_shipped
    accuracy_pct = (total_shipped / total_expected * 100) if total_expected else 0
    backorder_pct = (total_variance / total_expected * 100) if total_expected else 0
    col1, col2 = st.columns(2)
    with col1:
        fig1 = go.Figure(go.Pie(values=[backorder_pct, 100 - backorder_pct], hole=0.65, marker_colors=['#ff9999', '#e6e6e6'], textinfo='none'))
        fig1.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250,
                           annotations=[dict(text=f"{backorder_pct:.1f}%", x=0.5, y=0.55, font_size=22, showarrow=False),
                                        dict(text=f"{int(total_variance)} Variance", x=0.5, y=0.35, font_size=12, showarrow=False)])
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = go.Figure(go.Pie(values=[accuracy_pct, 100 - accuracy_pct], hole=0.65, marker_colors=['#7cd992', '#e6e6e6'], textinfo='none'))
        fig2.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250,
                           annotations=[dict(text=f"{accuracy_pct:.1f}%", x=0.5, y=0.55, font_size=22, showarrow=False),
                                        dict(text=f"{int(missed)} Missed", x=0.5, y=0.35, font_size=12, showarrow=False)])
        st.plotly_chart(fig2, use_container_width=True)


# ---------- DATE LOGIC ----------
date_list = []
days_checked = 0
#current_date = datetime.today().date()
current_date = date(2025,8,13)
while len(date_list) < 3 and days_checked < 7:
    weekday = current_date.weekday()  # Monday = 0, Sunday = 6

    if weekday == 6:  # Sunday - always skip
        current_date += timedelta(days=1)
        days_checked += 1
        continue

    if weekday == 5:  # Saturday
        # Filter to see if there are any GINo entries for this Saturday
        df_day = df[df['ExpDate'].dt.date == current_date]
        if df_day['GINo'].count() == 0:
            # No orders — skip Saturday
            current_date += timedelta(days=1)
            days_checked += 1
            continue

    # Valid day to display
    date_list.append(current_date)
    current_date += timedelta(days=1)
    days_checked += 1


# ---------- DISPLAY ----------
layout = []
for i in range(len(date_list)):
    layout.append(5)
    if i != len(date_list) - 1:
        layout.append(0.3)  # thinner divider
cols = st.columns(layout)

col_index = 0
for i, dash_date in enumerate(date_list):
    with cols[col_index]:
        df_day = df[df['ExpDate'].dt.date == dash_date]

        # --- Date Header ---
        st.markdown(
            f"<h5 style='text-align:center; color:gray; margin-bottom:10px;'>{dash_date.strftime('%d %b %Y')}</h5>",
            unsafe_allow_html=True
        )

        # --- TOP ROW: Urgent/Critical stacked + Completion Pie ---
        top1, top2 = st.columns([1, 1.5])   # pie gets more space
        with top1:
            st.markdown("##### 🚨 Critical Orders")
            critical_df = df_day[(df_day['Order Type'] == 'Ad-hoc Critical') & 
                                 (~df_day['Order Status'].isin(['Packed', 'Shipped']))]
            st.markdown(
                f"<div style='background-color:#f5a1a1; padding:10px; border-radius:8px; text-align:center;'>"
                f"🚨 Critical: {critical_df['GINo'].nunique()}</div>", unsafe_allow_html=True)
            if not critical_df.empty:
                st.dataframe(pd.DataFrame({"GI No": critical_df['GINo'].unique()}), key=f"{i}_critical")

            st.markdown("##### ⚠ Urgent Orders")
            urgent_df = df_day[(df_day['Order Type'] == 'Ad-hoc Urgent') & 
                               (~df_day['Order Status'].isin(['Packed', 'Shipped']))]
            st.markdown(
                f"<div style='background-color:#f8e5a1; padding:10px; border-radius:8px; text-align:center;'>"
                f"⚠ Urgent: {urgent_df['GINo'].nunique()}</div>", unsafe_allow_html=True)
            if not urgent_df.empty:
                st.dataframe(pd.DataFrame({"GI No": urgent_df['GINo'].unique()}), key=f"{i}_urgent")

        with top2:
            st.markdown("##### ✅ % Completion")
            daily_completed_pie(df_day, key_prefix=f"day{i}")

        # --- MIDDLE ROW: Order Status Table ---
        st.markdown("##### 📋 Order Status Table")
        order_status_matrix(df_day, key_prefix=f"day{i}")

        # --- BOTTOM ROW: Orders Breakdown Chart ---
        st.markdown("##### 📦 Orders Breakdown")
        daily_overview(df_day, key_prefix=f"day{i}")

    # vertical divider between dates
    if i != len(date_list) - 1:
        with cols[col_index + 1]:
            st.markdown(
                "<div style='height: 100%; border-left: 1px solid #bbb; margin: auto;'></div>",
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






















