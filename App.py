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
        '1-Normal': 'Normal',
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
    "order_types": ['Back Orders', 'Normal', 'Ad-hoc Normal', 'Ad-hoc Urgent', 'Ad-hoc Critical'],
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
    # Filter for files that start with 'aircon' (case-insensitive)
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

    /* ============================================================
       NEW: FULL WIDTH ORDER STATUS TABLE
       ============================================================ */

    /* Table container must stretch full width */
    .table-container {
        width: 100%;
        padding: 0;
        margin: 10px 0 20px 0;
        overflow-x: auto;   /* enable scroll if needed */
    }

    /* Make the table itself fill the width */
    .table-container table {
        width: 100% !important;
        border-collapse: collapse;
        margin: 0;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow: hidden;
    }

    /* Header cells */
    .table-container th {
        padding: 10px 12px;
        font-size: 13px;
        font-weight: 600;
        border: 1px solid #d1d5db;
        text-align: center;
        background-color: #f3f4f6;
        color: #374151;
        white-space: nowrap;
    }

    /* Body cells */
    .table-container td {
        padding: 8px 10px;
        font-size: 13px;
        border: 1px solid #e5e7eb;
        text-align: center;
        color: #1f2937;
    }

    /* Hover row */
    .table-container tbody tr:hover {
        background-color: #f9fafb;
    }

    /* Last row (Total) formatting */
    .table-container tbody tr:last-child {
        font-weight: 600;
        background-color: #f3f4f6;
    }

    /* Responsive for small screens */
    @media (max-width: 768px) {
        .table-container th,
        .table-container td {
            padding: 6px 6px;
            font-size: 11px;
        }
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

# Load data
df = load_data(file_stream)

# Filter df
aircon_zones = ['aircon', 'controlled drug room', 'strong room']
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)]

# Filter df by Type
valid_types = ["Disposal", "Goods Issue", "Forward Deploy"]
df['Type'] = df['Type'].astype(str).str.strip()
df = df[df['Type'].isin(valid_types)]


# ---------- DASHBOARD FUNCTIONS ----------

# Daily completed pie
def daily_completed_pie(df_today, dash_date, key_prefix=""):
    # Exclude cancelled orders from the total count
    df_active = df_today[df_today['Order Status'] != 'Cancelled']
    total_orders = df_active.shape[0]

    today = pd.Timestamp.today().normalize().date()
    
    # Determine what "completed" means based on the date
    if dash_date == today:
        # Today's orders: Different criteria based on order type
        # Ad-hoc Critical/Urgent should be shipped
        # All others should be at least packed
        critical_urgent_shipped = df_active[
            (df_active['Order Type'].isin(['Ad-hoc Critical', 'Ad-hoc Urgent'])) & 
            (df_active['Order Status'] == 'Shipped')
        ].shape[0]
        
        others_packed_or_shipped = df_active[
            (~df_active['Order Type'].isin(['Ad-hoc Critical', 'Ad-hoc Urgent'])) & 
            (df_active['Order Status'].isin(['Packed', 'Shipped']))
        ].shape[0]
        
        completed_orders = critical_urgent_shipped + others_packed_or_shipped
        completed_label = "Completed"
    else:
        # D+1 and D+2 orders: All should be packed or shipped
        completed_orders = df_active['Order Status'].isin(['Packed', 'Shipped']).sum()
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
        width=180,
        height=180,
        margin=dict(l=5, r=5, t=5, b=5),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(size=10)
        ),
        annotations=[dict(text=f"{completed_pct:.1f}%", x=0.5, y=0.5, font_size=16, showarrow=False)]
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_completed")


def order_status_matrix(df_today, key_prefix=""):
    # --- Build pivot table ---
    df_status_table = df_today.groupby(["Order Type", "Order Status"]).size().unstack(fill_value=0)

    df_status_table = df_status_table.reindex(
        index=CONFIG['order_types'],
        columns=CONFIG['status_segments'],
        fill_value=0
    )

    df_status_table["Total"] = df_status_table.sum(axis=1)

    total_row = df_status_table.sum(axis=0)
    total_row.name = "Total"

    df_status_table = pd.concat([df_status_table, total_row.to_frame().T])


    # --- Cell highlighter ---
    def highlight_cell(val, row_name, col_name):
        # Don't highlight totals or completed statuses
        if col_name in ["Shipped", "Cancelled", "Total"]:
            return ""
        if val <= 0:
            return ""

        if row_name == "Ad-hoc Urgent":
            return "background-color: #f8e5a1"
        if row_name == "Ad-hoc Critical":
            return "background-color: #f5a1a1"
        if row_name == "Ad-hoc Normal":
            return "background-color: #ADD8E6"
        return ""


    # --- Build style dataframe ---
    def highlight_df(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for r in df.index:
            if r == "Total":
                continue
            for c in df.columns:
                styles.at[r, c] = highlight_cell(df.at[r, c], r, c)
        return styles


    # --- Apply style ---
    styled_df = (
        df_status_table.style
            .apply(highlight_df, axis=None)
            .set_table_styles([{
                "selector": "th",
                "props": [
                    ("padding", "8px 10px"),
                    ("font-size", "12px"),
                    ("font-weight", "600"),
                    ("border", "1px solid #d1d5db"),
                    ("text-align", "center"),
                    ("background-color", "#f3f4f6"),
                    ("color", "#374151"),
                ],
            }, {
                "selector": "td",
                "props": [
                    ("padding", "6px 8px"),
                    ("font-size", "12px"),
                    ("border", "1px solid #e5e7eb"),
                    ("text-align", "center"),
                    ("color", "#1f2937"),
                ],
            }, {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("width", "100%"),  # Ensures full width
                    ("margin", "0 auto"),
                    ("box-shadow", "0 1px 3px rgba(0,0,0,0.1)"),
                    ("border-radius", "8px"),
                    ("overflow", "hidden"),
                ],
            }, {
                "selector": "tbody tr:hover",
                "props": [
                    ("background-color", "#f9fafb"),
                ],
            }, {
                "selector": "tbody tr:last-child",
                "props": [
                    ("font-weight", "600"),
                    ("background-color", "#f3f4f6"),
                ],
            }])
            .format("{:.0f}")
    )

    # --- Render HTML using supported method ---
    html_code = styled_df.to_html()

    with st.container():
        components.html(
            f"""
            <div class="table-container">
                {html_code}
            </div>
            """,
            height=400,  # You can adjust this height based on your content size
            scrolling=True
        )




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
# Create tabs
tab1, tab2 = st.tabs(["📊 Daily Dashboard", "📈 Analytics"])

with tab1:
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
                f"<h3 style='text-align:center; color:#4b5563; margin-bottom:8px; font-weight:bold;'>{dash_date.strftime('%d %b %Y')}</h3>",
                unsafe_allow_html=True
            )

            # --- Orders Breakdown Metrics ---
            brk_col1, brk_col2, brk_col3 = st.columns([1.5, 1, 1])
            
            with brk_col1:
                st.markdown("<h5 style='margin-bottom:8px;'>📦 Orders Breakdown</h5>", unsafe_allow_html=True)
            
            with brk_col2:
                st.markdown(
                    f"""
                    <div style='
                        background-color: #f9fafb;
                        padding: 8px 10px;
                        border-radius: 8px;
                        text-align: center;
                        font-size: 14px;
                        line-height: 1.3;
                        border: 1px solid #e5e7eb;
                    '>
                        <div style='font-weight: 600; font-size: 18px; color:#111827;'>{df_day.shape[0]}</div>
                        <div style='color: #6b7280; font-size: 12px;'>📄 Order Lines</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with brk_col3:
                st.markdown(
                    f"""
                    <div style='
                        background-color: #f9fafb;
                        padding: 8px 10px;
                        border-radius: 8px;
                        text-align: center;
                        font-size: 14px;
                        line-height: 1.3;
                        border: 1px solid #e5e7eb;
                    '>
                        <div style='font-weight: 600; font-size: 18px; color:#111827;'>{df_day['GINo'].nunique()}</div>
                        <div style='color: #6b7280; font-size: 12px;'>📦 No. of GIs</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

            # --- TOP ROW: Urgent/Critical stacked + Completion Pie ---
            top1, top2 = st.columns([1, 1.5])   # pie gets more space
            with top1:
                # Determine completion criteria based on date
                today = pd.Timestamp.today().normalize().date()
                
                # Critical Orders Section
                if dash_date == today:
                    # Today: critical orders outstanding = not shipped
                    critical_df = df_day[(df_day['Order Type'] == 'Ad-hoc Critical') & 
                                         (~df_day['Order Status'].isin(['Shipped', 'Cancelled']))]
                else:
                    # D+1 and D+2: critical orders outstanding = not packed/shipped
                    critical_df = df_day[(df_day['Order Type'] == 'Ad-hoc Critical') & 
                                         (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))]
                
                critical_gis = critical_df['GINo'].unique().tolist() if not critical_df.empty else []
                critical_text = ", ".join(map(str, critical_gis))
                
                # Expandable copy section
                with st.expander(f"🚨 Critical Orders ({len(critical_gis)})", expanded=True):
                    col_label, col_copy = st.columns([4, 1])
                    with col_label:
                        st.markdown("**GI Numbers:**")
                    with col_copy:
                        if critical_text:
                            components.html(f"""
                                <button onclick="navigator.clipboard.writeText('{critical_text}').then(() => alert('✅ Copied!'))" 
                                        style="background-color: transparent; border: none; cursor: pointer; font-size: 20px; padding: 0;">
                                    📋
                                </button>
                            """, height=30)
                    st.text_area(
                        "GI Numbers:",
                        value=critical_text if critical_text else "No critical orders",
                        height=100,
                        key=f"{i}_critical_copy_text",
                        label_visibility="collapsed"
                    )
                
                # Urgent Orders Section
                st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                
                if dash_date == today:
                    # Today: urgent orders outstanding = not shipped
                    urgent_df = df_day[(df_day['Order Type'] == 'Ad-hoc Urgent') & 
                                       (~df_day['Order Status'].isin(['Shipped', 'Cancelled']))]
                else:
                    # D+1 and D+2: urgent orders outstanding = not packed/shipped
                    urgent_df = df_day[(df_day['Order Type'] == 'Ad-hoc Urgent') & 
                                       (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))]
                
                urgent_gis = urgent_df['GINo'].unique().tolist() if not urgent_df.empty else []
                urgent_text = ", ".join(map(str, urgent_gis))
                
                # Expandable copy section
                with st.expander(f"⚠️ Urgent Orders ({len(urgent_gis)})", expanded=True):
                    col_label, col_copy = st.columns([4, 1])
                    with col_label:
                        st.markdown("**GI Numbers:**")
                    with col_copy:
                        if urgent_text:
                            components.html(f"""
                                <button onclick="navigator.clipboard.writeText('{urgent_text}').then(() => alert('✅ Copied!'))" 
                                        style="background-color: transparent; border: none; cursor: pointer; font-size: 20px; padding: 0;">
                                    📋
                                </button>
                            """, height=30)
                    st.text_area(
                        "GI Numbers:",
                        value=urgent_text if urgent_text else "No urgent orders",
                        height=100,
                        key=f"{i}_urgent_copy_text",
                        label_visibility="collapsed"
                    )

            with top2:
                st.markdown("<h5 style='text-align:center; margin-bottom:8px;'>✅ % Completion</h5>", unsafe_allow_html=True)
                daily_completed_pie(df_day, dash_date, key_prefix=f"day{i}")
                
                # Outstanding Orders Section
                st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                
                # Determine outstanding orders based on date and order type
                today = pd.Timestamp.today().normalize().date()
                
                if dash_date == today:
                    # Today: different criteria based on order type
                    # Critical/Urgent outstanding = not shipped
                    critical_urgent_outstanding = df_day[
                        (df_day['Order Type'].isin(['Ad-hoc Critical', 'Ad-hoc Urgent'])) & 
                        (~df_day['Order Status'].isin(['Shipped', 'Cancelled']))
                    ]
                    # Others outstanding = not packed/shipped
                    others_outstanding = df_day[
                        (~df_day['Order Type'].isin(['Ad-hoc Critical', 'Ad-hoc Urgent'])) & 
                        (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))
                    ]
                    outstanding_df = pd.concat([critical_urgent_outstanding, others_outstanding])
                else:
                    # D+1 and D+2: outstanding = not packed/shipped (excluding cancelled)
                    outstanding_df = df_day[
                        (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))
                    ]
                
                outstanding_gis = outstanding_df['GINo'].unique().tolist() if not outstanding_df.empty else []
                outstanding_text = ", ".join(map(str, outstanding_gis))
                
                # Expandable copy section for outstanding orders
                with st.expander(f"⏳ Outstanding Orders ({len(outstanding_gis)})", expanded=True):
                    col_label, col_copy = st.columns([4, 1])
                    with col_label:
                        st.markdown("**GI Numbers:**")
                    with col_copy:
                        if outstanding_text:
                            components.html(f"""
                                <button onclick="navigator.clipboard.writeText('{outstanding_text}').then(() => alert('✅ Copied!'))" 
                                        style="background-color: transparent; border: none; cursor: pointer; font-size: 20px; padding: 0;">
                                    📋
                                </button>
                            """, height=30)
                    st.text_area(
                        "GI Numbers:",
                        value=outstanding_text if outstanding_text else "No outstanding orders",
                        height=100,
                        key=f"{i}_outstanding_copy_text",
                        label_visibility="collapsed"
                    )


            # --- MIDDLE ROW: Order Status Table ---
            st.markdown("<h5 style='margin-top:12px; margin-bottom:8px;'>📋 Order Status Table</h5>", unsafe_allow_html=True)
            order_status_matrix(df_day, key_prefix=f"day{i}")


        # vertical divider between dates
        if i != len(date_list) - 1:
            with cols[col_index + 1]:
                st.markdown(
                    "<div style='border-left: 1px solid #bbb; height: 1000px; margin: auto;'></div>",
                    unsafe_allow_html=True
                )

        col_index += 2

with tab2:
    # ---------- ANALYTICS TAB ----------
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Order Lines (Past 14 Days)")
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



