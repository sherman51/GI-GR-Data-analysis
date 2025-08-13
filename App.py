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

# ---------- HEADER ----------
st.markdown(
    """
    <div style="display: flex; align-items: center; background-color: #e3f2f0; padding: 8px 12px; border-radius: 6px;">
        <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" 
             style="max-height:40px; height:auto; width:auto; margin-right:10px;">
        <h3 style="margin: 0; font-family: Arial, sans-serif; color: #333333;">
            - <b>Outbound Dashboard</b>
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")
uploaded_file = st.sidebar.file_uploader("📂 Upload Excel File", type=["xlsx"])
selected_date = st.sidebar.date_input("Select Date to View", datetime.today())

# ---------- HELPER FUNCTIONS ----------
def load_data(file):
    df = pd.read_excel(file, skiprows=6)
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

def pie_chart(value, label, total_label, height=300):
    fig = go.Figure(go.Pie(
        values=[value, 100 - value],
        labels=[label, 'Remaining'],
        marker_colors=['mediumseagreen', 'lightgray'],
        hole=0.7,
        textinfo='none',
        sort=False
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=height,
        annotations=[
            dict(text=f"{value:.2f}%", x=0.5, y=0.5, font_size=20, showarrow=False),
            dict(text=total_label, x=0.5, y=0.2, font_size=12, showarrow=False)
        ]
    )
    return fig

# ---------- SECTION FUNCTIONS ----------
def daily_overview(df_today):
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
        labels=["Completed (Packed/Shipped)", "Remaining"],
        marker_colors=['mediumseagreen', 'lightgray'],
        hole=0.6,
        textinfo='none',
        sort=False
    ))
    fig.update_layout(
        showlegend=True,
        margin=dict(t=0, b=0, l=0, r=0),
        height=300,
        annotations=[dict(text=f"{completed_pct:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False)]
    )
    st.plotly_chart(fig, use_container_width=True)

def order_status_matrix(df_today):
    df_status_table = df_today.groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)
    df_status_table = df_status_table.reindex(index=CONFIG['order_types'],
                                              columns=CONFIG['status_segments'],
                                              fill_value=0)
    st.dataframe(df_status_table, height=300)

def adhoc_orders_section(df_today):
    adhoc_df = df_today[df_today['Order Type'].isin(['Ad-hoc Urgent', 'Ad-hoc Critical'])]
    grouped = adhoc_df.groupby(['GINo', 'Order Type']).size().unstack(fill_value=0)
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
        height=400,
        margin=dict(l=10, r=10, t=30, b=30)
    )
    st.plotly_chart(fig, use_container_width=True)

def expiry_date_summary(df):
    recent_df = df[df['ExpDate'] >= pd.Timestamp.today() - pd.Timedelta(days=14)]
    daily_summary = recent_df.groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
    cancelled_summary = recent_df[recent_df['Status'] == '98-Cancelled'] \
        .groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
    dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
    orders_received = [daily_summary.get(date, 0) for date in dates]
    orders_cancelled = [cancelled_summary.get(date, 0) for date in dates]
    fig = go.Figure(data=[
        go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='lightgreen'),
        go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='red')
    ])
    fig.update_layout(
        barmode='group',
        xaxis_title='Expiry Date',
        yaxis_title='Order Count',
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)

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
    col1.plotly_chart(pie_chart(backorder_pct, "Back Order", f"{int(total_variance)} Variance", height=350), use_container_width=True)

    col2.markdown("**Order Accuracy %**")
    missed = total_expected - total_shipped
    col2.plotly_chart(pie_chart(accuracy_pct, "Accuracy", f"{int(missed)} Missed", height=350), use_container_width=True)

# ---------- MAIN LAYOUT ----------
if uploaded_file:
    df = load_data(uploaded_file)
    df_today = df[df['ExpDate'].dt.date == selected_date]

    # Top Date Display
    st.markdown(f"### Date: {datetime.now().strftime('%d %b %Y')}")
    st.markdown("---")

    # Create main 2-column layout
    left_col, right_col = st.columns([2, 2])

    # ===== LEFT COLUMN =====
    with left_col:
        st.subheader("Orders Completed Today")
        daily_completed_pie(df_today)
        st.subheader("Daily Outbound Overview")
        daily_overview(df_today)
        st.subheader("Expiry Date Summary")
        expiry_date_summary(df)

    # ===== RIGHT COLUMN =====
    with right_col:
        st.subheader("Orders Status Table")
        order_status_matrix(df_today)
        st.subheader("Ad-hoc Orders by GINo")
        adhoc_orders_section(df_today)
        st.subheader("Performance Metrics")
        performance_metrics(df)

    st.markdown("---")
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.warning("📄 Please upload an Excel file to begin.")





