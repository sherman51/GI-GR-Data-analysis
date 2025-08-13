import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ---------------- CONFIG ----------------
CONFIG = {
    'order_types': [
        'Planned Delivery', 
        'Ad-hoc Normal', 
        'Ad-hoc Urgent', 
        'Ad-hoc Critical'
    ],
    'status_segments': [
        'Completed', 
        'In Progress', 
        'Pending'
    ],
    'colors': {
        'Completed': '#2ca02c',
        'In Progress': '#ff7f0e',
        'Pending': '#d62728'
    }
}

# ---------------- SAMPLE DATA (replace with your own df_today) ----------------
def load_data():
    data = {
        'Order Type': [
            'Planned Delivery', 'Planned Delivery', 'Ad-hoc Normal',
            'Ad-hoc Urgent', 'Ad-hoc Critical', 'Ad-hoc Critical'
        ],
        'Order Status': [
            'Completed', 'Pending', 'In Progress', 'Completed', 'Pending', 'Completed'
        ],
        'GINo': [1, 2, 3, 4, 5, 6]
    }
    return pd.DataFrame(data)

df_today = load_data()
selected_date = datetime.today()

# ---------------- DAILY OVERVIEW ----------------
def daily_overview(df_today):
    col_date, col_orders, col_unique = st.columns(3)
    with col_date:
        st.metric(label="Date", value=selected_date.strftime('%d %b %Y'))
    with col_orders:
        st.metric(label="Total Order Lines", value=df_today.shape[0])
    with col_unique:
        st.metric(label="Unique GINo Today", value=df_today['GINo'].nunique())

    order_types = CONFIG['order_types']
    segments = CONFIG['status_segments']
    colors = CONFIG['colors']

    # Prepare data
    data = {seg: [] for seg in segments}
    for ot in order_types:
        ot_df = df_today[df_today['Order Type'] == ot]
        for seg in segments:
            data[seg].append((ot_df['Order Status'] == seg).sum())

    all_counts = sum(data.values(), [])

    # Calculate percentages
    percentages = {
        seg: [
            (val / sum(all_counts) * 100) if sum(all_counts) > 0 else 0
            for val in data[seg]
        ]
        for seg in segments
    }

    # Create figure
    bar_fig = go.Figure()

    # Main bars
    for seg in segments:
        bar_fig.add_trace(go.Bar(
            y=order_types,
            x=data[seg],
            name=seg,
            orientation='h',
            marker=dict(color=colors[seg])
        ))

    # Overlay percentage markers
    for seg in segments:
        bar_fig.add_trace(go.Scatter(
            y=order_types,
            x=[v if v > 0 else None for v in data[seg]],
            mode='markers+text',
            text=[f"{p:.1f}%" if p > 0 else "" for p in percentages[seg]],
            textposition="middle right",
            marker=dict(color=colors[seg], size=8, symbol="circle"),
            showlegend=False
        ))

    bar_fig.update_layout(
        barmode='stack',
        xaxis_title="Order Count",
        xaxis_type="linear",
        margin=dict(l=10, r=10, t=30, b=30),
        height=400
    )

    st.plotly_chart(bar_fig, use_container_width=True)

# ---------------- APP ----------------
st.set_page_config(page_title="Daily Overview", layout="wide")
st.title("📊 Date Outbound Orders")
daily_overview(df_today)
