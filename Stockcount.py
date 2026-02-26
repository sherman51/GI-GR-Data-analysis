from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import storage
from google.oauth2 import service_account
import io
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


def download_latest_excel(bucket):
    blobs = list(bucket.list_blobs())
    count_blobs = [b for b in blobs if b.name.lower().startswith('count') and b.name.lower().endswith(('.xlsx', '.xls'))]
    if not count_blobs:
        return None, None
    latest_blob = max(count_blobs, key=lambda b: b.updated)
    file_bytes = latest_blob.download_as_bytes()
    return io.BytesIO(file_bytes), latest_blob.name


# ---------- FETCH LATEST FILE ----------
file_stream, file_name = download_latest_excel(bucket)
if file_stream:
    file_stream.seek(0)
    st.sidebar.success(f"📥 Using latest file: {file_name}")
    st.sidebar.info(f"🔄 Last refresh: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.sidebar.error("❌ No Count Excel files found in GCS bucket.")
    st.stop()

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


# ---------- LOAD DATA ----------
@st.cache_data(ttl=60)
def load_data(_file_bytes, fname):
    df = pd.read_excel(io.BytesIO(_file_bytes), engine='openpyxl')
    df.columns = df.columns.str.strip()
    df.dropna(axis=1, how="all", inplace=True)
    df.dropna(how="all", inplace=True)

    for col in ['OnHand', 'Count', 'Variance']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Lot1' in df.columns:
        df['ExpiryDate'] = pd.to_datetime(df['Lot1'], errors='coerce')

    return df


file_stream.seek(0)
raw_bytes = file_stream.read()
df = load_data(raw_bytes, file_name)

# Sidebar summary
st.sidebar.metric("Total Line Items", df.shape[0])
st.sidebar.metric("Count Numbers", df['Number'].nunique())
st.sidebar.metric("Lines with Variance", int((df['Variance'] != 0).sum()))

# ---------- SUMMARY METRICS ----------
total_lines = len(df)
lines_with_variance = int((df['Variance'] != 0).sum())
lines_zero_variance = int((df['Variance'] == 0).sum())
accuracy_pct = (lines_zero_variance / total_lines * 100) if total_lines > 0 else 0
variance_lines_pos = int((df['Variance'] > 0).sum())
variance_lines_neg = int((df['Variance'] < 0).sum())

tab1, tab2 = st.tabs(["📊 Count Dashboard", "📋 Variance Details"])

# ===================== TAB 1: DASHBOARD =====================
with tab1:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # --- ROW 1: 3 Key Metrics ---
    c1, c2, c3, _pad = st.columns([1, 1, 1, 3])
    with c1:
        st.metric("📄 Total Lines", f"{total_lines:,}")
    with c2:
        st.metric("✅ Zero Variance", f"{lines_zero_variance:,}")
    with c3:
        st.metric("⚠️ Lines w/ Variance", f"{lines_with_variance:,}")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- ROW 2: Accuracy donut + Variance breakdown bar ---
    col_left, col_mid = st.columns([1, 1.6])

    with col_left:
        st.markdown("#### ✅ Count Accuracy")
        fig_acc = go.Figure(go.Pie(
            values=[accuracy_pct, 100 - accuracy_pct],
            labels=["Accurate", "Variance"],
            marker_colors=['#22c55e', '#ef4444'],
            hole=0.62,
            textinfo='none',
            sort=False
        ))
        fig_acc.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            annotations=[dict(text=f"{accuracy_pct:.1f}%", x=0.5, y=0.5, font_size=22, showarrow=False, font_color="#111")]
        )
        st.plotly_chart(fig_acc, use_container_width=True, key="acc_donut")

    with col_mid:
        st.markdown("#### ⚠️ Variance Breakdown")
        fig_var = go.Figure(go.Bar(
            x=["Gain (+)", "Loss (−)", "Zero"],
            y=[variance_lines_pos, variance_lines_neg, lines_zero_variance],
            marker_color=['#3b82f6', '#ef4444', '#22c55e'],
            text=[variance_lines_pos, variance_lines_neg, lines_zero_variance],
            textposition='outside'
        ))
        fig_var.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="No. of Lines",
            showlegend=False,
            plot_bgcolor='white',
            yaxis=dict(gridcolor='#f0f0f0')
        )
        st.plotly_chart(fig_var, use_container_width=True, key="var_bar")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # --- ROW 3: Variance lines only table (with Location) ---
    st.markdown("#### 📋 Count Sheets Summary — Variance Lines Only")

    df_var_only = df[df['Variance'] != 0].copy()

    if df_var_only.empty:
        st.success("🎉 No variance lines found! All counts match system quantities.")
    else:
        display_cols = ['Number', 'LineID', 'SKUCode', 'Description', 'Location', 'OnHand', 'Count', 'Variance']
        if 'ExpiryDate' in df_var_only.columns:
            display_cols.append('ExpiryDate')
        if 'Remarks' in df_var_only.columns:
            display_cols.append('Remarks')

        var_display = df_var_only[[c for c in display_cols if c in df_var_only.columns]].copy()

        def highlight_var_row(row):
            color = '#dcfce7' if row['Variance'] > 0 else '#fee2e2'
            return [f'background-color: {color}' if col == 'Variance' else '' for col in row.index]

        fmt = {'OnHand': '{:,.0f}', 'Count': '{:,.0f}', 'Variance': '{:+,.0f}'}
        if 'ExpiryDate' in var_display.columns:
            fmt['ExpiryDate'] = lambda x: x.strftime('%d-%b-%Y') if pd.notna(x) else ''

        styled_summary = var_display.style \
            .apply(highlight_var_row, axis=1) \
            .format(fmt) \
            .set_table_styles([
                {"selector": "th", "props": [
                    ("background-color", "#f3f4f6"), ("font-weight", "600"),
                    ("font-size", "12px"), ("padding", "6px 10px"),
                    ("border", "1px solid #d1d5db"), ("text-align", "center")
                ]},
                {"selector": "td", "props": [
                    ("font-size", "12px"), ("padding", "5px 10px"),
                    ("border", "1px solid #e5e7eb"), ("text-align", "center")
                ]},
                {"selector": "table", "props": [
                    ("border-collapse", "collapse"), ("width", "100%"),
                    ("font-family", "'Segoe UI', sans-serif")
                ]}
            ])

        components.html(
            f"<style>body{{margin:0;font-family:'Segoe UI',sans-serif;}}</style>{styled_summary.to_html()}",
            height=420,
            scrolling=True
        )


# ===================== TAB 2: VARIANCE DETAILS =====================
with tab2:
    st.markdown("### ⚠️ Lines with Variance")

    df_var = df[df['Variance'] != 0].copy()

    if df_var.empty:
        st.success("🎉 No variance lines found! All counts match system quantities.")
    else:
        st.markdown(f"**{len(df_var)} line(s) with variance found**")

        # Derive zone for filter
        df_var['Zone'] = df_var['Location'].astype(str).str[:1]

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            var_type = st.selectbox("Variance Type", ["All", "Gain (+)", "Loss (−)"])
        with f2:
            count_nums = ["All"] + sorted(df_var['Number'].unique().tolist())
            sel_count = st.selectbox("Count Number", count_nums)
        with f3:
            zones_avail = ["All"] + sorted(df_var['Zone'].unique().tolist())
            sel_zone = st.selectbox("Zone", zones_avail)

        # Apply filters
        filtered = df_var.copy()
        if var_type == "Gain (+)":
            filtered = filtered[filtered['Variance'] > 0]
        elif var_type == "Loss (−)":
            filtered = filtered[filtered['Variance'] < 0]
        if sel_count != "All":
            filtered = filtered[filtered['Number'] == sel_count]
        if sel_zone != "All":
            filtered = filtered[filtered['Zone'] == sel_zone]

        # Display columns
        display_cols = ['Number', 'LineID', 'SKUCode', 'Description', 'Location', 'OnHand', 'Count', 'Variance']
        if 'ExpiryDate' in filtered.columns:
            display_cols.append('ExpiryDate')
        if 'Remarks' in filtered.columns:
            display_cols.append('Remarks')

        display_df = filtered[[c for c in display_cols if c in filtered.columns]].copy()

        def highlight_var_row2(row):
            color = '#dcfce7' if row['Variance'] > 0 else '#fee2e2'
            return [f'background-color: {color}' if col == 'Variance' else '' for col in row.index]

        fmt2 = {'OnHand': '{:,.0f}', 'Count': '{:,.0f}', 'Variance': '{:+,.0f}'}
        if 'ExpiryDate' in display_df.columns:
            fmt2['ExpiryDate'] = lambda x: x.strftime('%d-%b-%Y') if pd.notna(x) else ''

        styled_var = display_df.style \
            .apply(highlight_var_row2, axis=1) \
            .format(fmt2) \
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
            height=500,
            scrolling=True
        )

        # Summary stats
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
