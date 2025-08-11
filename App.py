from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random

# ---------- Page Config ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ---------- Header ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")

# ---------- Summary Metrics ----------
col1, col2 = st.columns(2)
with col1:
    st.metric("Past 2 Weeks Orders", "506")
with col2:
    st.metric("Avg. Daily Orders", "50.6")

# ---------- Orders Bar Chart ----------
st.markdown("#### 📊 Orders Over the Past 2 Weeks")

dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
orders_received = [random.randint(30, 70) for _ in range(14)]
orders_cancelled = [random.randint(0, 10) for _ in range(14)]

fig = go.Figure(data=[
    go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='lightgreen'),
    go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='red')
])
fig.update_layout(barmode='group', xaxis_title='Date', yaxis_title='Order Count')
st.plotly_chart(fig, use_container_width=True)

# ---------- Daily Orders + Breakdown Section ----------
st.markdown("#### 📦 Daily Outbound Overview")
st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")

col_do, col_chart = st.columns([1, 5])

with col_do:
    st.metric("Daily Outbound Orders", "84")

with col_chart:
    order_types = [
        "Back Orders (Accumulated)",
        "Scheduled Orders",
        "Ad-hoc Normal Orders",
        "Ad-hoc Urgent Orders",
        "Ad-hoc Critical Orders"
    ]
    segments = ["Tpt Booked", "Packed", "Picked", "Open"]
    colors = ['green', 'blue', 'yellow', 'salmon']

    data = {
        seg: [random.randint(1, 10) for _ in order_types]
        for seg in segments
    }

    bar_fig = go.Figure()
    for seg, color in zip(segments, colors):
        bar_fig.add_trace(go.Bar(
            y=order_types,
            x=data[seg],
            name=seg,
            orientation='h',
            marker=dict(color=color)
        ))
    bar_fig.update_layout(
        barmode='stack',
        xaxis_title='Order Count',
        margin=dict(l=10, r=10, t=30, b=30),
        height=400
    )
    st.plotly_chart(bar_fig, use_container_width=True)

# ---------- Performance Meters ----------
st.markdown("#### 📈 Performance Metrics")
col3, col4 = st.columns(2)

with col3:
    st.markdown("**Back Order < 0.50%**")
    st.progress(0.001, text="0.10% (1 of 1000 lines)")

with col4:
    st.markdown("**Order Accuracy > 99.50%**")
    st.progress(1.0, text="100.00% (0 SLA Missed)")

# ---------- Order Status Table ----------
st.markdown("#### 📋 Order Status Table")

table_data = {
    "Ad-hoc Critical Orders": [3, 0, 3, 0],
    "Ad-hoc Urgent Orders": [4, 2, 0, 0],
    "Ad-hoc Normal Orders": [10, 7, 3, 0],
    "Scheduled Orders": [5, 6, 13, 17],
    "Back Orders (Accumulated)": [2, 4, 3, 2]
}
index_labels = ["Tpt Booked", "Packed", "Picked", "Open"]
df_table = pd.DataFrame(table_data, index=index_labels)
st.dataframe(df_table)

# ---------- Footer ----------
st.markdown("---")
st.markdown("### 💙 *Stay Safe & Well*")

