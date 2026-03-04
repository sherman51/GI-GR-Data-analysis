from datetime import datetime, timezone
import io
import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# ---------- CONFIG ----------
st.set_page_config(layout="wide", page_title="Stock Count Dashboard", page_icon="📊")

# ---------- AUTO REFRESH ----------
refresh_count = st_autorefresh(interval=60 * 1000, limit=None, key="data_refresh")

# ---------- GCP AUTH ----------
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
BUCKET_NAME = "testbucket352"
gcs_client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = gcs_client.bucket(BUCKET_NAME)


# ---------- DOWNLOAD WITH VALIDATION ----------
def download_latest_excel(bucket):
    try:
        blobs = list(bucket.list_blobs())
    except Exception as e:
        st.sidebar.error(f"❌ Could not list GCS bucket: {e}")
        return None, None

    count_blobs = [
        b for b in blobs
        if 'count' in b.name.lower() and b.name.lower().endswith(('.xlsx', '.xls'))
    ]

    if not count_blobs:
        return None, None

    # Skip blobs updated in the last 15 seconds (may still be uploading)
    now_utc = datetime.now(timezone.utc)
    stable_blobs = [
        b for b in count_blobs
        if (now_utc - b.updated).total_seconds() > 15
    ]

    candidate_blobs = stable_blobs if stable_blobs else count_blobs
    latest_blob = max(candidate_blobs, key=lambda b: b.updated)

    try:
        file_bytes = latest_blob.download_as_bytes()
    except Exception as e:
        st.sidebar.error(f"❌ Failed to download '{latest_blob.name}': {e}")
        return None, None

    if len(file_bytes) < 200:
        st.sidebar.error(
            f"❌ File '{latest_blob.name}' is too small "
            f"({len(file_bytes)} bytes) — may be empty or corrupt."
        )
        return None, None

    return io.BytesIO(file_bytes), latest_blob.name


# ---------- SPREADSHEETML PARSER (XML-based .xls) ----------
def parse_spreadsheetml(raw_bytes):
    """
    Parse Excel XML / SpreadsheetML format .xls files.
    Handles broken xmlns URIs with embedded whitespace/newlines —
    common in files exported from ERP/WMS systems.
    """
    from lxml import etree

    content = raw_bytes.decode('utf-8', errors='replace')

    # Strip anything before <Workbook
    content = re.sub(r'^.*?(<Workbook)', r'\1', content, flags=re.DOTALL)

    # Generic fix: remove whitespace inside ANY xmlns="..." URI
    content = re.sub(r'(xmlns:\w+="[^"]*?)\s+([^"]*?")', r'\1\2', content)

    # Escape bare ampersands
    content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

    try:
        tree = etree.fromstring(content.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Failed to parse SpreadsheetML XML: {e}")

    ns = 'urn:schemas-microsoft-com:office:spreadsheet'
    rows = tree.findall(f'.//{{{ns}}}Row')

    if not rows:
        raise ValueError("No rows found in SpreadsheetML file.")

    data = []
    for row in rows:
        cells = row.findall(f'.//{{{ns}}}Data')
        data.append([c.text if c.text else '' for c in cells])

    if not data:
        raise ValueError("Parsed rows but found no cell data.")

    df = pd.DataFrame(data[1:], columns=data[0])
    return df


# ---------- FETCH LATEST FILE ----------
file_stream, file_name = download_latest_excel(bucket)
if file_stream is None:
    st.sidebar.error("❌ No valid Count Excel files found in GCS bucket.")
    st.stop()

st.sidebar.success(f"📥 Using latest file: {file_name}")
st.sidebar.info(f"🔄 Last refresh: {datetime.now().strftime('%H:%M:%S')}")

# ---------- GLOBAL STYLE ----------
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0 !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    [data-testid="metric-container"] {
        border: 0.5px solid #cccccc;
        padding: 6px 10px;
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
        font-size: 14px;
        font-weight: 400;
        margin-bottom: 4px;
        color: #333333;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] p {
        font-size: 22px;
        font-weight: 700;
        margin-top: 2px;
        color: #000000;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 600;
    }
    @media (max-width: 1600px) { html { zoom: 0.95; } }
    @media (max-width: 1400px) { html { zoom: 0.90; } }
    @media (max-width: 1200px) { html { zoom: 0.82; } }
</style>
""", unsafe_allow_html=True)

# ---------- PAGE HEADER ----------
components.html("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
        .header-container {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            background: linear-gradient(90deg, #003366, #2563eb);
            padding: 14px 18px;
            border-radius: 10px;
            gap: 20px;
        }
        .header-left { display: flex; align-items: center; }
        .header-left img { max-height: 42px; height: auto; width: auto; margin-right: 12px; }
        .header-left h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 24px; }
        #clock { font-size: 26px; font-weight: 700; color: #ffffff; white-space: nowrap; }
    </style>
</head>
<body>
    <div class="header-container">
        <div class="header-left">
            <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" alt="Logo">
            <h2>Stock Count Dashboard</h2>
        </div>
        <div id="clock">-- --- --:--:--</div>
    </div>
    <script>
        function updateClock() {
            const now = new Date();
            const dd = String(now.getDate()).padStart(2, '0');
            const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
            const mmm = monthNames[now.getMonth()];
            const h = String(now.getHours()).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('clock').textContent = dd + " " + mmm + " " + h + ":" + m + ":" + s;
        }
        updateClock();
        setInterval(updateClock, 1000);
    </script>
</body>
</html>
""", height=85)


# ---------- LOAD DATA WITH FULL FORMAT SUPPORT ----------
@st.cache_data(ttl=60)
def load_data(_file_bytes, fname):
    raw_bytes = _file_bytes
    buf = io.BytesIO(raw_bytes)

    # Detect file format from magic bytes
    is_xlsx = raw_bytes[:4] == b'PK\x03\x04'
    is_biff  = raw_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    is_xml   = (
        b'<Workbook' in raw_bytes[:500]
        or b'spreadsheet' in raw_bytes[:500].lower()
    )

    df = None
    last_error = None

    if is_xlsx or fname.lower().endswith('.xlsx'):
        try:
            df = pd.read_excel(buf, engine='openpyxl')
        except Exception as e:
            last_error = e

    elif is_biff:
        try:
            df = pd.read_excel(buf, engine='xlrd')
        except Exception as e:
            last_error = e

    elif is_xml:
        try:
            df = parse_spreadsheetml(raw_bytes)
        except Exception as e:
            last_error = e

    else:
        # Last-resort: try all engines
        for engine in ['openpyxl', 'xlrd']:
            buf.seek(0)
            try:
                df = pd.read_excel(buf, engine=engine)
                break
            except Exception as e:
                last_error = e

    if df is None:
        raise ValueError(
            f"Could not read '{fname}'. The file may be corrupt or unsupported. "
            f"Last error: {last_error}"
        )

    df.columns = df.columns.str.strip()
    df.dropna(axis=1, how="all", inplace=True)
    df.dropna(how="all", inplace=True)

    # OnHand and Variance: blanks treated as 0
    for col in ['OnHand', 'Variance']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Count: preserve NaN to distinguish blank (not counted) from 0 (counted as zero)
    if 'Count' in df.columns:
        df['Count'] = pd.to_numeric(df['Count'], errors='coerce')

    if 'Lot1' in df.columns:
        df['ExpiryDate'] = pd.to_datetime(df['Lot1'], errors='coerce')

    # Counted: blank Count = not yet counted, any number including 0 = counted
    df['Counted'] = df['Count'].notna()

    return df


# ---------- READ & PARSE ----------
file_stream.seek(0)
raw_bytes = file_stream.read()

try:
    df = load_data(raw_bytes, file_name)
except ValueError as e:
    st.error(f"❌ Failed to load Excel file: {e}")
    st.stop()

# ---------- OVERALL COMPLETION METRICS ----------
total_lines = len(df)
total_counted = int(df['Counted'].sum())
total_remaining = total_lines - total_counted
overall_pct = (total_counted / total_lines * 100) if total_lines > 0 else 0

# Variance stats
lines_with_variance = int((df['Variance'] != 0).sum())
variance_lines_pos = int((df['Variance'] > 0).sum())
variance_lines_neg = int((df['Variance'] < 0).sum())

# Sidebar
st.sidebar.metric("Total Line Items", f"{total_lines:,}")
st.sidebar.metric("Lines Counted", f"{total_counted:,}")
st.sidebar.metric("Lines Remaining", f"{total_remaining:,}")

tab1, tab2 = st.tabs(["📊 Count Progress", "📋 Variance Details"])

# ===================== TAB 1: COUNT PROGRESS =====================
with tab1:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2, c3, _pad = st.columns([1, 1, 1, 3])
    with c1:
        st.metric("📄 Total Lines", f"{total_lines:,}")
    with c2:
        st.metric("✅ Lines Counted", f"{total_counted:,}")
    with c3:
        st.metric("⏳ Remaining", f"{total_remaining:,}")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col_donut, col_table = st.columns([1, 2])

    with col_donut:
        st.markdown("#### 📊 Overall Completion")
        fig_overall = go.Figure(go.Pie(
            values=[overall_pct, 100 - overall_pct],
            labels=["Counted", "Remaining"],
            marker_colors=['#22c55e', '#e5e7eb'],
            hole=0.65,
            textinfo='none',
            sort=False
        ))
        fig_overall.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            annotations=[
                dict(text=f"{overall_pct:.1f}%", x=0.5, y=0.58, font_size=26, showarrow=False, font_color="#111", font=dict(weight='bold')),
                dict(text=f"{total_counted}/{total_lines}", x=0.5, y=0.4, font_size=13, showarrow=False, font_color="#6b7280")
            ]
        )
        st.plotly_chart(fig_overall, use_container_width=True, key="overall_donut")

    with col_table:
        st.markdown("#### 📋 Progress by ICC Number")

        icc_summary = df.groupby('Number').agg(
            Total=('Counted', 'count'),
            Counted=('Counted', 'sum'),
        ).reset_index()
        icc_summary['Remaining'] = icc_summary['Total'] - icc_summary['Counted']
        icc_summary['Completion_%'] = (icc_summary['Counted'] / icc_summary['Total'] * 100).round(1)

        if 'icc_sort_col' not in st.session_state:
            st.session_state['icc_sort_col'] = 'Number'
            st.session_state['icc_sort_asc'] = True

        icc_summary = icc_summary.sort_values(
            by=st.session_state['icc_sort_col'],
            ascending=st.session_state['icc_sort_asc']
        ).reset_index(drop=True)

        def sort_arrow(col_key):
            if st.session_state['icc_sort_col'] == col_key:
                return ' ▲' if st.session_state['icc_sort_asc'] else ' ▼'
            return ' ⇅'

        h0, h1, h2, h3, h4 = st.columns([2, 1.2, 1.2, 1.2, 2])

        def make_sort_button(col, label, col_key):
            if col.button(f"{label}{sort_arrow(col_key)}", key=f"sort_{col_key}", use_container_width=True):
                if st.session_state['icc_sort_col'] == col_key:
                    st.session_state['icc_sort_asc'] = not st.session_state['icc_sort_asc']
                else:
                    st.session_state['icc_sort_col'] = col_key
                    st.session_state['icc_sort_asc'] = True

        make_sort_button(h0, "ICC Number",   "Number")
        make_sort_button(h1, "Total",        "Total")
        make_sort_button(h2, "Counted",      "Counted")
        make_sort_button(h3, "Remaining",    "Remaining")
        make_sort_button(h4, "Completion %", "Completion_%")

        rows_html = ""
        for _, row in icc_summary.iterrows():
            pct = row['Completion_%']
            bar_color = '#22c55e' if pct == 100 else ('#f97316' if pct >= 50 else '#ef4444')
            row_bg = '#f0fdf4' if pct == 100 else 'white'

            bar_html = f"""
                <div style="background:#e5e7eb; border-radius:4px; height:14px; width:100%;">
                    <div style="background:{bar_color}; width:{pct}%; height:14px; border-radius:4px;"></div>
                </div>
                <div style="font-size:11px; color:#6b7280; margin-top:2px;">{pct:.1f}%</div>
            """
            status_icon = "✅" if pct == 100 else ("🟡" if pct >= 50 else "🔴")

            rows_html += f"""
                <tr style="background-color:{row_bg}; border-bottom: 1px solid #e5e7eb;">
                    <td style="padding:8px 10px; font-weight:600; font-size:12px;">{status_icon} {row['Number']}</td>
                    <td style="padding:8px 10px; text-align:center; font-size:12px;">{int(row['Total']):,}</td>
                    <td style="padding:8px 10px; text-align:center; font-size:12px; color:#16a34a; font-weight:600;">{int(row['Counted']):,}</td>
                    <td style="padding:8px 10px; text-align:center; font-size:12px; color:#dc2626; font-weight:600;">{int(row['Remaining']):,}</td>
                    <td style="padding:8px 20px; min-width:160px;">{bar_html}</td>
                </tr>
            """

        table_html = f"""
        <style>
            body {{ margin: 0; font-family: 'Segoe UI', sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            tbody tr:hover {{ background-color: #f9fafb !important; }}
            td {{ vertical-align: middle; }}
        </style>
        <table><tbody>{rows_html}</tbody></table>
        """
        components.html(table_html, height=500, scrolling=True)


# ===================== TAB 2: VARIANCE DETAILS =====================
with tab2:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    v1, v2, v3, _pad = st.columns([1, 1, 1, 3])
    with v1:
        st.metric("⚠️ Lines w/ Variance", f"{lines_with_variance:,}")
    with v2:
        st.metric("📈 Gain Lines", f"{variance_lines_pos:,}")
    with v3:
        st.metric("📉 Loss Lines", f"{variance_lines_neg:,}")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col_chart, col_space = st.columns([1.5, 2])
    with col_chart:
        st.markdown("#### ⚠️ Variance Breakdown")
        fig_var = go.Figure(go.Bar(
            x=["Gain (+)", "Loss (−)"],
            y=[variance_lines_pos, variance_lines_neg],
            marker_color=['#3b82f6', '#ef4444'],
            text=[variance_lines_pos, variance_lines_neg],
            textposition='outside'
        ))
        fig_var.update_layout(
            height=240,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="No. of Lines",
            showlegend=False,
            plot_bgcolor='white',
            yaxis=dict(gridcolor='#f0f0f0')
        )
        st.plotly_chart(fig_var, use_container_width=True, key="var_bar")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("#### 📋 Variance Issue Summary")

    df_var = df[df['Variance'] != 0].copy()

    if df_var.empty:
        st.success("🎉 No variance lines found! All counts match system quantities.")
    else:
        df_var['Zone'] = df_var['Location'].astype(str).str[:1]

        f1, f2, f3 = st.columns(3)
        with f1:
            var_type = st.selectbox("Variance Type", ["All", "Gain (+)", "Loss (−)"])
        with f2:
            count_nums = ["All"] + sorted(df_var['Number'].unique().tolist())
            sel_count = st.selectbox("Count Number", count_nums)
        with f3:
            zones_avail = ["All"] + sorted(df_var['Zone'].unique().tolist())
            sel_zone = st.selectbox("Zone", zones_avail)

        filtered = df_var.copy()
        if var_type == "Gain (+)":
            filtered = filtered[filtered['Variance'] > 0]
        elif var_type == "Loss (−)":
            filtered = filtered[filtered['Variance'] < 0]
        if sel_count != "All":
            filtered = filtered[filtered['Number'] == sel_count]
        if sel_zone != "All":
            filtered = filtered[filtered['Zone'] == sel_zone]

        display_cols = ['Number', 'LineID', 'SKUCode', 'Description', 'Location', 'OnHand', 'Count', 'Variance']
        if 'ExpiryDate' in filtered.columns:
            display_cols.append('ExpiryDate')
        if 'Remarks' in filtered.columns:
            display_cols.append('Remarks')

        display_df = filtered[[c for c in display_cols if c in filtered.columns]].copy()
        display_df['Count'] = display_df['Count'].apply(
            lambda x: '' if pd.isna(x) else f"{int(x):,}"
        )

        def highlight_var_row(row):
            color = '#dcfce7' if row['Variance'] > 0 else '#fee2e2'
            return [f'background-color: {color}' if col == 'Variance' else '' for col in row.index]

        fmt = {'OnHand': '{:,.0f}', 'Variance': '{:+,.0f}'}
        if 'ExpiryDate' in display_df.columns:
            fmt['ExpiryDate'] = lambda x: x.strftime('%d-%b-%Y') if pd.notna(x) else ''

        styled_var = display_df.style \
            .apply(highlight_var_row, axis=1) \
            .format(fmt) \
            .set_table_styles([
                {"selector": "th", "props": [
                    ("background-color", "#f3f4f6"), ("font-weight", "600"),
                    ("font-size", "12px"), ("padding", "6px 10px"),
                    ("border", "1px solid #d1d5db")
                ]},
                {"selector": "td", "props": [
                    ("font-size", "12px"), ("padding", "5px 10px"),
                    ("border", "1px solid #e5e7eb")
                ]},
                {"selector": "table", "props": [
                    ("border-collapse", "collapse"), ("width", "100%"),
                    ("font-family", "'Segoe UI', sans-serif")
                ]}
            ])

        components.html(
            f"<style>body{{margin:0;font-family:'Segoe UI',sans-serif;}}</style>{styled_var.to_html()}",
            height=450,
            scrolling=True
        )

        st.markdown("---")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Filtered Lines", len(filtered))
        with s2:
            st.metric("Total Gain (Qty)", f"{int(filtered[filtered['Variance'] > 0]['Variance'].sum()):+,}")
        with s3:
            st.metric("Total Loss (Qty)", f"{int(filtered[filtered['Variance'] < 0]['Variance'].sum()):+,}")
        with s4:
            st.metric("Net Variance (Qty)", f"{int(filtered['Variance'].sum()):+,}")
