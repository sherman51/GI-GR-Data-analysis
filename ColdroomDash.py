from datetime import datetime, timedelta, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
import io
from streamlit_autorefresh import st_autorefresh

# ---------- CONFIG ----------
st.set_page_config(layout="wide", page_title="ColdRoom Dashboard", page_icon="📊")

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
st_autorefresh(interval=150*1000, limit=None, key="data_refresh")

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

    /* Page container */
    .block-container {
        padding-top: 0.5rem !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* Divider */
    hr {
        border: none;
        height: 1px;
        background-color: #e5e7eb;
        margin: 2rem 0;
    }

    /* Metric cards */
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
</style>
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

# Load data
df = load_data(file_stream)

# Filter df
coldroom_zones = ['cold room', 'freezer']
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(coldroom_zones)]

# ---------- DASHBOARD FUNCTIONS ----------
def daily_overview(df_today, key_prefix=""):
    segments = CONFIG['status_segments']
    colors = CONFIG['colors']

    normal_type = 'normal'
    adhoc_types = ['Ad-hoc Critical', 'Ad-hoc Urgent', 'Ad-hoc Normal']
    all_order_types = [normal_type] + adhoc_types

    order_data = {seg: {ot: 0 for ot in all_order_types} for seg in segments}
    for ot in all_order_types:
        ot_df = df_today[df_today['Order Type'] == ot]
        for seg in segments:
            order_data[seg][ot] = (ot_df['Order Status'] == seg).sum()

    # Find max Ad-hoc count among all segments and types
    max_adhoc_count = 0
    for seg in segments:
        for ot in adhoc_types:
            count = order_data[seg][ot]
            if count > max_adhoc_count:
                max_adhoc_count = count

    # Set x-axis range for Ad-hoc chart with a bit of padding
    adhoc_xaxis_range = [0, (max_adhoc_count + 5)]

    fig = go.Figure()

    # Primary axis: Normal orders (stacked horizontally)
    for seg in segments:
        fig.add_trace(go.Bar(
            y=[normal_type],
            x=[order_data[seg][normal_type]],
            name=f"{seg}",
            orientation='h',
            marker_color=colors.get(seg),
            legendgroup=seg
        ))

    # Secondary axis: Ad-hoc orders (stacked horizontally on x2 axis)
    for seg in segments:
        fig.add_trace(go.Bar(
            y=adhoc_types,
            x=[order_data[seg][ot] for ot in adhoc_types],
            name=f"{seg} (Ad-hoc)",
            orientation='h',
            marker_color=colors.get(seg),
            legendgroup=seg,
            xaxis='x2',
            showlegend=False
        ))

    fig.update_layout(
        barmode='stack',
        height=40 * len(all_order_types) + 100,
        margin=dict(l=10, r=10, t=40, b=20),
        xaxis=dict(title='Normal Order Count'),
        xaxis2=dict(title='Ad-hoc Order Count', overlaying='x', side='top', showgrid=False, range=adhoc_xaxis_range),
        yaxis=dict(
            categoryorder='array',
            categoryarray=[normal_type] + adhoc_types,
            automargin=True
        ),
    )

    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_combined")








# Daily completed pie
def daily_completed_pie(df_today, dash_date, key_prefix=""):
    total_orders = df_today.shape[0]

    today = pd.Timestamp.today().normalize().date()
    is_today = dash_date == today

    if is_today:
        completed_orders = df_today['Order Status'].isin(['Shipped']).sum()
        completed_label = "Completed (Shipped)"
    else:
        completed_orders = df_today['Order Status'].isin(['Packed']).sum()
        completed_label = "Completed (Packed)"

    completed_pct = (completed_orders / total_orders * 100) if total_orders else 0

    fig = go.Figure(go.Pie(
        values=[completed_pct, 100 - completed_pct],
        labels=[completed_label, "Outstanding"],
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
    # Group and pivot the data
    df_status_table = df_today.groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)
    df_status_table = df_status_table.reindex(index=CONFIG['order_types'],
                                              columns=CONFIG['status_segments'],
                                              fill_value=0)
    # Add a Total column (sum across status segments)
    df_status_table['Total'] = df_status_table.sum(axis=1)
    # Add a Total row (sum across order types)
    total_row = df_status_table.sum(axis=0)
    total_row.name = 'Total'
    df_status_table = pd.concat([df_status_table, total_row.to_frame().T])

    # Highlighting logic for Urgent, Critical, and Ad-hoc Normal
    def highlight_cell(val, row_name, col_name):
        exclude_status = ['Shipped', 'Cancelled', 'Total']
        if col_name in exclude_status or val <= 0:
            return ''
        if row_name == 'Ad-hoc Urgent':
            return 'background-color: #f8e5a1'
        elif row_name == 'Ad-hoc Critical':
            return 'background-color: #f5a1a1'
        elif row_name == 'Ad-hoc Normal':
            return 'background-color: #ADD8E6'
        else:
            return ''

    # Apply highlight only to original rows (exclude Total row)
    def highlight_df(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        for r in df.index:
            for c in df.columns:
                # Skip highlighting for Total row
                if r == 'Total':
                    continue
                styles.at[r, c] = highlight_cell(df.at[r, c], r, c)
        return styles

    styled_df = (df_status_table.style
                 .apply(highlight_df, axis=None)
                 .set_table_styles([
                     {'selector': 'th, td',
                      'props': [
                          ('padding', '3px 6px'),
                          ('font-size', '12px'),
                          ('border-collapse', 'collapse'),
                          ('text-align', 'center'),
                      ]},
                     {'selector': 'table',
                      'props': [
                          ('table-layout', 'auto'),   # Autofit columns
                          ('width', 'auto'),
                          ('border-collapse', 'collapse'),
                      ]}
                 ])
                 .set_caption("Order Status Matrix with Totals")
                 .format("{:.0f}")
                 )

    st.write(styled_df, key=f"{key_prefix}_status")






# Ad-hoc orders
def adhoc_orders_section(df_today, key_prefix=""):
    not_completed_df = df_today[~df_today['Status'].isin(['Shipped'])]
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
current_date = datetime.today().date()
#current_date = date(2025,8,15)
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
            f"<h3 style='text-align:center; color:gray; margin-bottom:10px; font-weight:bold;'>{dash_date.strftime('%d %b %Y')}</h4>",
            unsafe_allow_html=True
        )

        # --- TOP ROW: Urgent/Critical stacked + Completion Pie ---
        top1, top2 = st.columns([1, 1.5])   # pie gets more space
        with top1:
            st.markdown("##### 🚨 Critical Orders")
            critical_df = df_day[(df_day['Order Type'] == 'Ad-hoc Critical') & 
                                 (~df_day['Order Status'].isin(['Shipped']))]
            st.markdown(
                f"<div style='background-color:#f5a1a1; padding:10px; border-radius:8px; text-align:center;'>"
                f"🚨 Critical: {critical_df['GINo'].nunique()}</div>", unsafe_allow_html=True)
            if not critical_df.empty:
                st.dataframe(pd.DataFrame({"GI No": critical_df['GINo'].unique()}), key=f"{i}_critical")

            st.markdown("##### ⚠ Urgent Orders")
            urgent_df = df_day[(df_day['Order Type'] == 'Ad-hoc Urgent') & 
                               (~df_day['Order Status'].isin(['Shipped']))]
            st.markdown(
                f"<div style='background-color:#f8e5a1; padding:10px; border-radius:8px; text-align:center;'>"
                f"⚠ Urgent: {urgent_df['GINo'].nunique()}</div>", unsafe_allow_html=True)
            if not urgent_df.empty:
                st.dataframe(pd.DataFrame({"GI No": urgent_df['GINo'].unique()}), key=f"{i}_urgent")

        with top2:
            st.markdown("##### ✅ % Completion")
            daily_completed_pie(df_day, dash_date, key_prefix=f"day{i}")


        # --- MIDDLE ROW: Order Status Table ---
        st.markdown("##### 📋 Order Status Table")
        order_status_matrix(df_day, key_prefix=f"day{i}")

        # --- BOTTOM ROW: Orders Breakdown Chart ---
        brk_col1, brk_col2, brk_col3 = st.columns([1.5, 1, 1])
        
        with brk_col1:
            st.markdown("##### 📦 Orders Breakdown")
        
        with brk_col2:
            st.markdown(
                f"""
                <div style='
                    background-color: #f4f4f4;
                    padding: 6px 10px;
                    border-radius: 6px;
                    text-align: center;
                    font-size: 14px;
                    line-height: 1.2;
                '>
                    <div style='font-weight: bold; font-size: 16px;'>{df_day.shape[0]}</div>
                    <div style='color: #555;'>🧾 Order Lines</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with brk_col3:
            st.markdown(
                f"""
                <div style='
                    background-color: #f4f4f4;
                    padding: 6px 10px;
                    border-radius: 6px;
                    text-align: center;
                    font-size: 14px;
                    line-height: 1.2;
                '>
                    <div style='font-weight: bold; font-size: 16px;'>{df_day['GINo'].nunique()}</div>
                    <div style='color: #555;'>📦 No. of GIs</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        
        daily_overview(df_day, key_prefix=f"day{i}")


    # vertical divider between dates
    if i != len(date_list) - 1:
        with cols[col_index + 1]:
            st.markdown(
                "<div style='border-left: 1px solid #bbb; height: 1000px; margin: auto;'></div>",
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























st.markdown("""
    <div style='text-align:center; color:#6b7280; font-size:0.9rem; margin-top:30px;'>
        ⭐ Stay Safe & Well ⭐
    </div>
""", unsafe_allow_html=True)


