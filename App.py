from datetime import datetime, timedelta, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
import io
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import hashlib

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
refresh_count = st_autorefresh(interval=60*1000, limit=None, key="data_refresh")

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
    file_stream.seek(0)  # Ensure we're at the start of the file
    st.sidebar.success(f"📥 Using latest file from GCS: {file_name}")
    st.sidebar.info(f"🔄 Last refresh: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.sidebar.error("❌ No Excel files found in GCS bucket.")
    st.stop()

# ---------- GLOBAL STYLE OVERRIDES ----------
st.markdown(
    """
    <style>
        /* ===============================
           GLOBAL PAGE PADDING & LAYOUT
        =============================== */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0 !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }

        .main .block-container {
            padding-top: 0.2rem !important;
        }

        /* Remove wide top margin before header */
        .st-emotion-cache-z5fcl4 {
            padding-top: 0 !important;
        }

        /* ===============================
           TITLES AND TEXT
        =============================== */
        .stMarkdown h2 {
            margin-bottom: 0rem !important;
        }

        .stMarkdown p {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
        }

        /* ===============================
           STREAMLIT METRIC STYLE FIXES
        =============================== */
        [data-testid="metric-container"] {
            border: 0.5px solid #cccccc;
            padding: 3px 10px;
            border-radius: 8px;
            background-color: white;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            margin: 0 !important;
            height: 90px;
        }

        [data-testid="metric-container"] > div {
            width: 100%;
            text-align: center;
            justify-content: center;
        }

        [data-testid="metric-container"] [data-testid="stMetricLabel"] p {
            font-size: 17px;
            font-weight: 400;
            margin-bottom: 4px;
            color: #333333;
        }

        [data-testid="metric-container"] [data-testid="stMetricValue"] p {
            font-size: 20px;
            font-weight: 700;
            margin-top: 2px;
            color: #000000;
        }

        /* Sale difference metrics */
        .metric-green {
            color: #34d399 !important;
            font-weight: bold !important;
        }
        .metric-red {
            color: #ef4444 !important;
            font-weight: bold !important;
        }

        /* ===============================
           TABS
        =============================== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 22px;
            justify-content: flex-start;
            padding-bottom: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 18px;
            font-weight: 600;
        }

        /* ===============================
           CALENDAR BOX LABELS
        =============================== */
        .stSelectbox label {
            font-size: 18px !important;
            font-weight: 600 !important;
        }

        /* Remove default calendar padding */
        .st-emotion-cache-1jicfl2 {
            padding-top: 0 !important;
            margin-top: -15px !important;
        }

        /* ===============================
           AUTO-FIT / AUTO-SCALE DASHBOARD
           (Keeps layout looking perfect at
            all zoom levels & screen sizes)
        =============================== */
        html {
            transform-origin: top left;
            zoom: 1;
        }

        @media (max-width: 1600px) { html { zoom: 0.95; } }
        @media (max-width: 1400px) { html { zoom: 0.90; } }
        @media (max-width: 1200px) { html { zoom: 0.80; } }
        @media (max-width: 1000px) { html { zoom: 0.70; } }
        @media (max-width: 800px)  { html { zoom: 0.60; } }
        @media (max-width: 600px)  { html { zoom: 0.50; } }

        /* Ensure tables and columns shrink cleanly */
        .dataframe {
            width: 100% !important;
        }

    </style>
    """,
    unsafe_allow_html=True
)





# ---------- PAGE HEADER ----------
components.html(
    """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', sans-serif;
            }
            .header-container {
                display: flex;
                align-items: center;
                justify-content: flex-start;   /* 🔥 Fix spacing */
                background: linear-gradient(90deg, #003366, #2563eb);
                padding: 14px 18px;
                border-radius: 10px;
                gap: 20px;                     /* 🔥 Add small spacing */
            }
            .header-left {
                display: flex;
                align-items: center;
            }
            .header-left img {
                max-height: 42px;
                height: auto;
                width: auto;
                margin-right: 12px;
            }
            .header-left h2 {
                margin: 0;
                color: #ffffff;
                font-weight: 600;
                font-size: 24px;
            }
            #clock {
                font-size: 26px;
                font-weight: 700;
                color: #ffffff;
                white-space: nowrap;
            }
        </style>
    </head>
    <body>
        <div class="header-container">
            <div class="header-left">
                <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" alt="Logo">
                <h2>Outbound Dashboard Aircon</h2>
            </div>
            <div id="clock">-- --- --:--:--</div>
        </div>

        <script>
            function updateClock() {
                const now = new Date();

                const dd = String(now.getDate()).padStart(2, '0');

                const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                const mmm = monthNames[now.getMonth()];

                const h = String(now.getHours()).padStart(2, '0');
                const m = String(now.getMinutes()).padStart(2, '0');
                const s = String(now.getSeconds()).padStart(2, '0');

                document.getElementById('clock').textContent =
                    dd + " " + mmm + " " + h + ":" + m + ":" + s;
            }

            updateClock();
            setInterval(updateClock, 1000);
        </script>
    </body>
    </html>
    """,
    height=85
)


# ---------- HELPER FUNCTIONS ----------
def load_data(file):
    """Load and clean data from Excel file."""
    try:
        # Seek to beginning to ensure clean read
        file.seek(0)
        df = pd.read_excel(file, skiprows=6, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ Failed to read Excel file: {str(e)}")
        st.stop()
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Remove empty rows and columns
    df.dropna(axis=1, how="all", inplace=True)
    df.dropna(how="all", inplace=True)
    
    # Convert date columns
    for col in ['ExpDate', 'CreatedOn', 'ShippedOn']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Filter out rows without ExpDate
    df = df[df['ExpDate'].notna()].copy()  # .copy() ensures clean DataFrame
    
    # Map priority and status
    df['Order Type'] = df['Priority'].map(CONFIG['priority_map']).fillna(df['Priority'])
    df['Status'] = df['Status'].astype(str).str.strip()
    df['Order Status'] = df['Status'].map(CONFIG['status_map']).fillna('Open')
    
    return df

# Load data - create fresh copy
df = load_data(file_stream)

# Filter df - use .copy() to ensure clean filtering
aircon_zones = ['aircon', 'controlled drug room', 'strong room']
df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)].copy()

# Filter df by Type
valid_types = ["Back Order","Disposal", "Goods Issue", "Forward Deploy"]
df['Type'] = df['Type'].astype(str).str.strip()
df = df[df['Type'].isin(valid_types)].copy()

# Verify data freshness
st.sidebar.metric("Total Records", df.shape[0])
st.sidebar.metric("Unique GI Numbers", df['GINo'].nunique())

# Create a data hash for keys - this will change when data changes
data_hash = hashlib.md5(f"{df.shape[0]}_{df['GINo'].sum() if 'GINo' in df.columns else 0}_{refresh_count}".encode()).hexdigest()[:8]


# ---------- DASHBOARD FUNCTIONS ----------
# Daily completed pie
def daily_completed_pie(df_today, dash_date, key_prefix=""):
    # Exclude cancelled orders from the total count
    df_active = df_today[df_today['Order Status'] != 'Cancelled']
    total_orders = df_active.shape[0]

    today = pd.Timestamp.today().normalize().date()
    
    # Determine what "completed" means based on the date
    if dash_date == today:
        # Today's orders: ALL must be shipped
        completed_orders = df_active[df_active['Order Status'] == 'Shipped'].shape[0]
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
        width=160,
        height=160,
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
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_completed_{data_hash}")

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
                    ("padding", "6px 8px"),  # Reduced padding
                    ("font-size", "11px"),  # Smaller font
                    ("font-weight", "600"),
                    ("font-family", "'Segoe UI', sans-serif"),
                    ("border", "1px solid #d1d5db"),
                    ("text-align", "center"),
                    ("background-color", "#f3f4f6"),
                    ("color", "#374151"),
                    ("width", "12.5%"),  # Equal width for 8 columns (7 status + 1 total)
                    ("min-width", "65px"),  # Reduced min-width
                ],
            }, {
                "selector": "td",
                "props": [
                    ("padding", "5px 6px"),  # Reduced padding
                    ("font-size", "11px"),  # Smaller font
                    ("font-family", "'Segoe UI', sans-serif"),
                    ("border", "1px solid #e5e7eb"),
                    ("text-align", "center"),
                    ("color", "#1f2937"),
                    ("width", "12.5%"),  # Equal width for all data cells
                    ("min-width", "65px"),  # Reduced min-width
                ],
            }, {
                "selector": "th:first-child, td:first-child",  # Row header (Order Type column)
                "props": [
                    ("width", "14%"),  # Slightly reduced width
                    ("min-width", "100px"),  # Reduced min-width
                    ("text-align", "left"),
                    ("padding-left", "10px"),  # Reduced padding
                ],
            }, {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("width", "100%"),
                    ("table-layout", "fixed"),  # KEY: Forces equal column widths
                    ("margin", "0 auto"),
                    ("box-shadow", "0 1px 3px rgba(0,0,0,0.1)"),
                    ("border-radius", "8px"),
                    ("overflow", "hidden"),
                    ("font-family", "'Segoe UI', sans-serif"),
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

    # --- Render HTML with injected font styling ---
    html_code = styled_df.to_html()

    with st.container():
        components.html(
            f"""
            <style>
                body, html {{
                    font-family: 'Segoe UI', sans-serif !important;
                    margin: 0;
                    padding: 0;
                }}
            </style>
            <div class="table-container">
                {html_code}
            </div>
            """,
            height=400,
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
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_expiry_{data_hash}")

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
        st.plotly_chart(fig1, use_container_width=True, key=f"{key_prefix}_backorder_{data_hash}")
    with col2:
        fig2 = go.Figure(go.Pie(values=[accuracy_pct, 100 - accuracy_pct], hole=0.65, marker_colors=['#7cd992', '#e6e6e6'], textinfo='none'))
        fig2.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250,
                           annotations=[dict(text=f"{accuracy_pct:.1f}%", x=0.5, y=0.55, font_size=22, showarrow=False),
                                        dict(text=f"{int(missed)} Missed", x=0.5, y=0.35, font_size=12, showarrow=False)])
        st.plotly_chart(fig2, use_container_width=True, key=f"{key_prefix}_accuracy_{data_hash}")


# ---------- DATE LOGIC ----------
date_list = []
days_checked = 0
current_date = datetime.today().date()
today = datetime.today().date()
#current_date = date(2025,8,15)

while len(date_list) < 3 and days_checked < 14:  # Extended to 14 days to find 3 valid days
    weekday = current_date.weekday()  # Monday = 0, Sunday = 6

    # Filter to see if there are any orders for this date
    df_day = df[df['ExpDate'].dt.date == current_date]
    
    # Exclude "Forward Deploy" orders for not today's order
    if current_date != today:
        df_day = df_day[df_day['Type'] != 'Forward Deploy']
    
    order_count = df_day['GINo'].count()

    # Skip if Sunday OR if no orders exist for this day
    if weekday == 6 or order_count == 0:
        current_date += timedelta(days=1)
        days_checked += 1
        continue

    # Valid day to display (has orders and not Sunday)
    date_list.append(current_date)
    current_date += timedelta(days=1)
    days_checked += 1

# If we couldn't find 3 days with orders, just use what we found
if len(date_list) == 0:
    st.warning("⚠️ No orders found in the next 14 days.")
    st.stop()

# ---------- DISPLAY ----------
tab1, tab2 = st.tabs(["📊 Daily Dashboard", "📈 Analytics"])


# ---------- FIXED CARD HELPER ----------
def fixed_card(title, body, key, height=150):
    st.markdown(
        f"""
        <div style="
            border:1px solid #d1d5db;
            border-radius:8px;
            padding:8px 10px;
            margin-bottom:10px;
            background:#ffffff;
            height:{height}px;
            box-sizing:border-box;
        ">
            <div style="font-weight:600;margin-bottom:6px;">{title}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.text_area(
        label="",
        value=body,
        height=height - 55,
        key=key
    )


with tab1:
    layout = []
    for i in range(len(date_list)):
        layout.append(5)
        if i != len(date_list) - 1:
            layout.append(0.3)

    cols = st.columns(layout)
    col_index = 0

    for i, dash_date in enumerate(date_list):
        with cols[col_index]:
            df_day = df[df['ExpDate'].dt.date == dash_date]
            today = pd.Timestamp.today().normalize().date()

            # ---------- DATE HEADER ----------
            st.markdown(
                f"<h3 style='text-align:center;color:#4b5563;font-weight:bold;'>"
                f"{dash_date.strftime('%d %b %Y')}</h3>",
                unsafe_allow_html=True
            )

            # ---------- BREAKDOWN ----------
            b1, b2, b3 = st.columns([1.5, 1, 1])
            with b1:
                st.markdown("### 📦 Orders Breakdown")
            with b2:
                st.metric("Order Lines", df_day.shape[0])
            with b3:
                st.metric("No. of GIs", df_day['GINo'].nunique())

            st.markdown("---")

            # ---------- TOP GRID (PERFECTLY ALIGNED) ----------
            left, right = st.columns(2)

            # ===== LEFT: PRIORITY ORDERS =====
            with left:
                st.markdown("### 🚨 Priority Orders")

                # ---- Critical ----
                if dash_date == today:
                    critical_df = df_day[
                        (df_day['Order Type'] == 'Ad-hoc Critical') &
                        (~df_day['Order Status'].isin(['Shipped', 'Cancelled']))
                    ]
                else:
                    critical_df = df_day[
                        (df_day['Order Type'] == 'Ad-hoc Critical') &
                        (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))
                    ]

                critical_gis = critical_df['GINo'].unique().tolist()
                critical_text = "\n".join(map(str, critical_gis)) or "No critical orders"

                fixed_card(
                    title=f"🚨 Critical Orders ({len(critical_gis)})",
                    body=critical_text,
                    key=f"{i}_critical_{data_hash}"
                )

                # ---- Urgent ----
                if dash_date == today:
                    urgent_df = df_day[
                        (df_day['Order Type'] == 'Ad-hoc Urgent') &
                        (~df_day['Order Status'].isin(['Shipped', 'Cancelled']))
                    ]
                else:
                    urgent_df = df_day[
                        (df_day['Order Type'] == 'Ad-hoc Urgent') &
                        (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))
                    ]

                urgent_gis = urgent_df['GINo'].unique().tolist()
                urgent_text = "\n".join(map(str, urgent_gis)) or "No urgent orders"

                fixed_card(
                    title=f"⚠️ Urgent Orders ({len(urgent_gis)})",
                    body=urgent_text,
                    key=f"{i}_urgent_{data_hash}"
                )

            # ===== RIGHT: STATUS OVERVIEW =====
            with right:
                st.markdown("### 📊 Status Overview")

                daily_completed_pie(df_day, dash_date, key_prefix=f"day{i}")

                if dash_date == today:
                    cu = df_day[
                        (df_day['Order Type'].isin(['Ad-hoc Critical', 'Ad-hoc Urgent'])) &
                        (~df_day['Order Status'].isin(['Shipped', 'Cancelled']))
                    ]
                    other = df_day[
                        (~df_day['Order Type'].isin(['Ad-hoc Critical', 'Ad-hoc Urgent'])) &
                        (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))
                    ]
                    outstanding_df = pd.concat([cu, other])
                else:
                    outstanding_df = df_day[
                        (~df_day['Order Status'].isin(['Packed', 'Shipped', 'Cancelled']))
                    ]

                outstanding_gis = outstanding_df['GINo'].unique().tolist()
                outstanding_text = "\n".join(map(str, outstanding_gis)) or "No outstanding orders"

                fixed_card(
                    title=f"⏳ Outstanding Orders ({len(outstanding_gis)})",
                    body=outstanding_text,
                    key=f"{i}_outstanding_{data_hash}"
                )

            # ---------- STATUS TABLE ----------
            st.markdown("### 📋 Order Status Table")
            order_status_matrix(df_day, key_prefix=f"day{i}")

        if i != len(date_list) - 1:
            with cols[col_index + 1]:
                st.markdown(
                    "<div style='border-left:1px solid #bbb;height:1000px;'></div>",
                    unsafe_allow_html=True
                )

        col_index += 2


# ---------- ANALYTICS TAB ----------
with tab2:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 📊 Order Lines (Past 14 Days)")
        order_volume_summary(df, key_prefix="overall")
        expiry_date_summary(df, key_prefix="overall")

    with c2:
        st.markdown("### 📈 Performance Metrics")
        performance_metrics(df, key_prefix="overall")




























