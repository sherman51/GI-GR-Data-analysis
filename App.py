from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------- CONFIG ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

CONFIG = {
    "priority_map": {
        '1-Normal': 'normal',
        '2-ADHOC Normal': 'Ad-hoc Normal',
        '3-ADHOC Urgent': 'Ad-hoc Urgent',
        '4-ADHOC Critical': 'Ad-hoc Critical'
    },
    "status_map": {
        '10-Open': 'Open',
        '45-Picked': 'Picked',
        '65-Packed': 'Packed',
        '75-Shipped': 'Shipped'
    },
    "order_types": ['Back Orders', 'normal', 'Ad-hoc Normal', 'Ad-hoc Urgent', 'Ad-hoc Critical'],
    "status_segments": ['Shipped', 'Packed', 'Picked', 'Open'],
    "colors": {
        'Shipped': 'green',
        'Packed': 'blue',
        'Picked': 'yellow',
        'Open': 'salmon',
        'Ad-hoc Urgent': 'orange',
        'Ad-hoc Critical': 'crimson'
    }
}

# ---------- PAGE HEADER ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
uploaded_file = st.sidebar.file_uploader(
    "📂 Upload Excel File", 
    type=["xlsx", "xls"]
)
selected_date = st.sidebar.date_input("Select Date to View", datetime.today())

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
    file_ext = file.name.split('.')[-1].lower()
    try:
        if file_ext == 'xls':
            df = pd.read_excel(file, skiprows=6, engine='xlrd')
        else:
            df = pd.read_excel(file, skiprows=6, engine='openpyxl')
    except ImportError:
        st.error("⚠ Missing dependency: Install `xlrd==1.2.0` for .xls files.")
        st.stop()

    df.columns = df.columns.str.strip()
    df.dropna(axis=1, how="all", inplace=True)
    df.dropna(how="all", inplace=True)

    for col in ['ExpDate', 'CreatedOn', 'ShippedOn']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # --- Normalize GI No to avoid duplicates like '123', '123.0', ' 123 ' ---
    # Keep original GINo for display, add a normalized copy for counting uniqueness
    df['GINo_orig'] = df.get('GINo')
    df['GINo'] = df['GINo'].where(df['GINo'].notna())  # preserve NaN
    df['GINo_norm'] = (
        df['GINo'].astype(str)
        .str.strip()
        .str.replace(r'\.0$', '', regex=True)  # remove trailing .0 from Excel floats
        .str.upper()
    )
    # Put NaN back where original was NaN/blank
    df.loc[df['GINo'].isna() | (df['GINo_norm'].str.lower().isin(['nan', 'none', ''])), 'GINo_norm'] = pd.NA

    # Business mappings
    df = df[df['ExpDate'].notna()]
    df['Order Type'] = df['Priority'].map(CONFIG['priority_map']).fillna(df['Priority'])
    df['Status'] = df['Status'].astype(str).str.strip()
    df['Order Status'] = df['Status'].map(CONFIG['status_map']).fillna('Open')

    # Precompute date-only to avoid repeated .dt.date calls
    df['ExpDate_date'] = df['ExpDate'].dt.date

    return df


def pie_chart(value, label, total_label):
    fig = go.Figure(go.Pie(
        values=[value, 100 - value],
        labels=[label, 'Outstanding'],
        marker_colors=['mediumseagreen', 'lightgray'],
        hole=0.7,
        textinfo='none',
        sort=False
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        annotations=[
            dict(text=f"{value:.2f}%", x=0.5, y=0.5, font_size=20, showarrow=False),
            dict(text=total_label, x=0.5, y=0.2, font_size=12, showarrow=False)
        ]
    )
    return fig


# ---------- SECTION FUNCTIONS ----------
def daily_overview(df_today):
    total_order_lines = df_today.shape[0]
    unique_gino = df_today['GINo_norm'].nunique()  # use normalized GI No

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div class='metric-container' style='background-color:#dce6dc;'>"
            f"<div class='metric-value'>{total_order_lines}</div>"
            f"<div class='metric-label'>📦 Total Order Lines</div>"
            f"</div>", unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div class='metric-container' style='background-color:#e6e1dc;'>"
            f"<div class='metric-value'>{unique_gino}</div>"
            f"<div class='metric-label'>🔢 Unique GINo Today</div>"
            f"</div>", unsafe_allow_html=True
        )

    order_types = CONFIG['order_types']
    segments = CONFIG['status_segments']
    colors = CONFIG['colors']

    data = {seg: [] for seg in segments}
    for ot in order_types:
        ot_df = df_today[df_today['Order Type'] == ot]
        for seg in segments:
            count = (ot_df['Order Status'] == seg).sum()
            data[seg].append(count)

    filtered_order_types = []
    filtered_data = {seg: [] for seg in segments}
    for idx, ot in enumerate(order_types):
        total = sum(data[seg][idx] for seg in segments)
        if total > 1:
            filtered_order_types.append(ot)
            for seg in segments:
                filtered_data[seg].append(data[seg][idx])

    bar_fig = go.Figure()
    for seg in segments:
        bar_fig.add_trace(go.Bar(
            y=filtered_order_types,
            x=filtered_data[seg],
            name=seg,
            orientation='h',
            marker=dict(color=colors[seg])
        ))

    bar_fig.update_layout(
        barmode='stack',
        xaxis_title="Order Count (log scale)",
        xaxis_type="log",
        margin=dict(l=10, r=10, t=30, b=30),
        height=400
    )

    st.plotly_chart(bar_fig, use_container_width=True)


def daily_completed_pie(df_today):
    total_orders = df_today.shape[0]
    completed_orders = df_today['Order Status'].isin(['Packed', 'Shipped']).sum()
    completed_pct = (completed_orders / total_orders * 100) if total_orders else 0

    fig = go.Figure(go.Pie(
        values=[completed_pct, 100 - completed_pct],
        labels=["Completed (Packed/Shipped)", "Outstanding"],
        marker_colors=['mediumseagreen', 'lightgray'],
        hole=0.6,
        textinfo='none',
        sort=False
    ))

    fig.update_layout(
        width=300,
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        annotations=[dict(text=f"{completed_pct:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False)]
    )

    st.plotly_chart(fig, use_container_width=True)


def order_status_matrix(df_today):
    df_status_table = df_today.groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)
    df_status_table = df_status_table.reindex(index=CONFIG['order_types'],
                                              columns=CONFIG['status_segments'],
                                              fill_value=0)
    st.dataframe(df_status_table)


def adhoc_orders_section(df_today):
    adhoc_df = df_today[df_today['Order Type'].isin(['Ad-hoc Urgent', 'Ad-hoc Critical'])]
    col1, col2 = st.columns(2)
    col1.metric(label="Ad-hoc Urgent Orders", value=(adhoc_df['Order Type'] == 'Ad-hoc Urgent').sum())
    col2.metric(label="Ad-hoc Critical Orders", value=(adhoc_df['Order Type'] == 'Ad-hoc Critical').sum())

    # Use normalized GI No for grouping to avoid duplicated labels
    grouped = adhoc_df.groupby(['GINo_norm', 'Order Type']).size().unstack(fill_value=0)
    if grouped.empty:
        st.info("No Ad-hoc Urgent or Critical orders for the selected date.")
        return
    fig = go.Figure()
    for col in grouped.columns:
        fig.add_trace(go.Bar(
            x=grouped.index,
            y=grouped[col],
            name=col,
            marker_color=CONFIG['colors'][col]
        ))
    fig.update_layout(
        barmode='group',
        xaxis_title='GINo',
        yaxis_title='Order Count',
        title='Ad-hoc Urgent & Critical Orders by GINo',
        height=500,
        margin=dict(l=10, r=10, t=30, b=30)
    )
    st.plotly_chart(fig, use_container_width=True)


def expiry_date_summary(df):
    # This chart still shows line counts; change to .nunique() if you prefer unique GI No here too
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
    st.plotly_chart(fig, use_container_width=True)


def order_volume_summary(df):
    # Last 14 days inclusive, unique by normalized GI No per day
    today = pd.Timestamp.today().normalize()
    start = today - pd.Timedelta(days=14)
    recent_df = df[(df['ExpDate'] >= start) & (df['ExpDate'] <= today)]

    # Use precomputed date-only and normalized GI No
    daily_counts = recent_df.groupby('ExpDate_date')['GINo_norm'].nunique(dropna=True)

    if daily_counts.empty:
        st.info("No orders found for the past 14 days.")
        return

    peak_day_vol = int(daily_counts.max())
    avg_vol = float(daily_counts.mean())
    low_day_vol = int(daily_counts.min())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"<div class='metric-container' style='background-color:#dce6dc;'>"
            f"<div class='metric-value'>{peak_day_vol}</div>"
            f"<div class='metric-label'>📈 Peak Day Volume (Unique GI)</div>"
            f"</div>", unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div class='metric-container' style='background-color:#e6e1dc;'>"
            f"<div class='metric-value'>{avg_vol:.1f}</div>"
            f"<div class='metric-label'>📊 Average Daily Volume (Unique GI)</div>"
            f"</div>", unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"<div class='metric-container' style='background-color:#e6dcdc;'>"
            f"<div class='metric-value'>{low_day_vol}</div>"
            f"<div class='metric-label'>📉 Lowest Day Volume (Unique GI)</div>"
            f"</div>", unsafe_allow_html=True
        )


def performance_metrics(df):
    today = pd.Timestamp.today().normalize()
    recent_past_df = df[(df['ExpDate'] < today) & (df['ExpDate'] >= today - pd.Timedelta(days=14))]
    total_expected = recent_past_df['ExpectedQTY'].sum()
    total_shipped = recent_past_df['ShippedQTY'].sum()
    accuracy_pct = (total_shipped / total_expected * 100) if total_expected else 0
    total_variance = recent_past_df['VarianceQTY'].sum()
    backorder_pct = (total_variance / total_expected * 100) if total_expected else 0

    col1, col2 = st.columns(2)
    col1.markdown("**Back Order %**")
    col1.plotly_chart(pie_chart(backorder_pct, "Back Order", f"{int(total_variance)} Variance"), use_container_width=True)

    col2.markdown("**Order Accuracy %**")
    missed = total_expected - total_shipped
    col2.plotly_chart(pie_chart(accuracy_pct, "Accuracy", f"{int(missed)} Missed"), use_container_width=True)


# ---------- MAIN ----------
if uploaded_file:
    df = load_data(uploaded_file)
    df_today = df[df['ExpDate_date'] == selected_date]

    st.markdown(
        f"<h5 style='margin-top:-10px; color:gray;'>{selected_date.strftime('%d %b %Y')}</h5>",
        unsafe_allow_html=True
    )

    # ====== ROW 1 ======
    row1_left, row1_right = st.columns([3, 2])
    with row1_left:
        st.markdown("#### ✅ % completion")
        daily_completed_pie(df_today)
    with row1_right:
        st.markdown("#### 📋 Order Status Table (Matrix Format)")
        order_status_matrix(df_today)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ====== ROW 2 ======
    row2_left, row2_right = st.columns([3, 2])
    with row2_left:
        st.markdown("#### 📦 Orders breakdown")
        daily_overview(df_today)
    with row2_right:
        st.markdown("#### 🚨 Urgent and Critical")
        adhoc_orders_section(df_today)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ====== ROW 3 ======
    row3_left, row3_right = st.columns([3, 2])
    with row3_left:
        st.markdown("#### 📊 Orders (Past 14 Days)")
        order_volume_summary(df)   # directly under the title
        expiry_date_summary(df)
    with row3_right:
        st.markdown("#### 📈 Performance Metrics")
        performance_metrics(df)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.warning("📄 Please upload an Excel file to begin.")
