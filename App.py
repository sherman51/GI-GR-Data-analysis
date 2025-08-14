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
        'Shipped': '#6BA292',        # muted green
        'Packed': '#8AA6A3',         # muted teal-gray
        'Picked': '#B8B8AA',         # muted beige-gray
        'Open': '#E2C391',           # muted gold
        'Ad-hoc Urgent': '#E28F83',  # muted coral
        'Ad-hoc Critical': '#C97064' # muted brick
    }
}

# ---------- PAGE HEADER ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
uploaded_file = st.sidebar.file_uploader("📂 Upload Excel File", type=["xlsx", "xls"])
selected_date = st.sidebar.date_input("Select Date to View", datetime.today())

st.markdown("""
<style>
hr { border: none; height: 1px; background-color: #d3d3d3; margin: 2rem 0; }
.counter-card {
    background-color: #f9f9f9;
    padding: 12px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 0 4px rgba(0,0,0,0.05);
}
.counter-value {
    font-size: 1.4rem;
    font-weight: bold;
    color: #333;
}
.counter-label {
    font-size: 0.9rem;
    color: #666;
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

    df = df[df['ExpDate'].notna()]
    df['Order Type'] = df['Priority'].map(CONFIG['priority_map']).fillna(df['Priority'])
    df['Status'] = df['Status'].astype(str).str.strip()
    df['Order Status'] = df['Status'].map(CONFIG['status_map']).fillna('Open')

    return df

def pie_chart(value, label, total_label):
    fig = go.Figure(go.Pie(
        values=[value, 100 - value],
        labels=[label, 'Outstanding'],
        marker_colors=['#6BA292', '#E0E0E0'],
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

def summary_counters(data, label_prefix=""):
    peak = data.max()
    avg = data.mean()
    low = data.min()

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='counter-card'><div class='counter-value'>{peak}</div><div class='counter-label'>{label_prefix} Peak Day Vol</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='counter-card'><div class='counter-value'>{avg:.1f}</div><div class='counter-label'>{label_prefix} Avg Vol</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='counter-card'><div class='counter-value'>{low}</div><div class='counter-label'>{label_prefix} Low Day Vol</div></div>", unsafe_allow_html=True)

# ---------- SECTION FUNCTIONS ----------
def daily_overview(df_today):
    daily_unique = df_today['GINo'].nunique()
    st.markdown("#### 📦 Orders Breakdown")
    summary_counters(pd.Series([daily_unique]), label_prefix="Today's")  # Single day summary

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

def expiry_date_summary(df):
    recent_df = df[df['ExpDate'] >= pd.Timestamp.today() - pd.Timedelta(days=14)]

    # Unique GINo counts instead of order lines
    daily_summary = recent_df.groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].nunique()
    cancelled_summary = recent_df[recent_df['Status'] == '98-Cancelled'] \
        .groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].nunique()

    # Fill missing dates
    dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
    orders_received = [daily_summary.get(date, 0) for date in dates]
    orders_cancelled = [cancelled_summary.get(date, 0) for date in dates]

    # Summary counters (Peak/Avg/Low)
    summary_counters(pd.Series(orders_received), label_prefix="Last 14 Days")

    # Chart
    fig = go.Figure(data=[
        go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='#8AA6A3'),
        go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='#E28F83')
    ])
    fig.update_layout(barmode='group', xaxis_title='Expiry Date', yaxis_title='Unique Orders')
    st.plotly_chart(fig, use_container_width=True)

# ---------- MAIN ----------
if uploaded_file:
    df = load_data(uploaded_file)
    df_today = df[df['ExpDate'].dt.date == selected_date]

    st.markdown(f"<h5 style='margin-top:-10px; color:gray;'>{selected_date.strftime('%d %b %Y')}</h5>", unsafe_allow_html=True)

    # Row 1
    row1_left, row1_right = st.columns([3, 2])
    with row1_left:
        st.markdown("#### ✅ % Completion")
        total_orders = df_today.shape[0]
        completed_orders = df_today['Order Status'].isin(['Packed', 'Shipped']).sum()
        completed_pct = (completed_orders / total_orders * 100) if total_orders else 0
        st.plotly_chart(pie_chart(completed_pct, "Completed", "Completion"), use_container_width=True)
    with row1_right:
        st.markdown("#### 📋 Order Status Table (Matrix Format)")
        order_status_matrix = df_today.groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)
        st.dataframe(order_status_matrix)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Row 2
    daily_overview(df_today)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Row 3
    st.markdown("#### 📊 Orders (Past 14 Days)")
    expiry_date_summary(df)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 💙 *Stay Safe & Well*")
else:
    st.warning("📄 Please upload an Excel file to begin.")
