from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ------------------------ PAGE CONFIG ------------------------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ------------------------ SIDEBAR FILE UPLOAD ------------------------
uploaded_file = st.sidebar.file_uploader("📤 Upload Excel File", type=["xlsx"])

# ------------------------ PROCESS FILE ------------------------
if uploaded_file:
    # Load data
    df_raw = pd.read_excel(uploaded_file, skiprows=5)
    df = df_raw.dropna(axis=1, how="all").dropna(how="all")

    # Convert types
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    num_cols = ['ExpectedQTY', 'ShippedQTY', 'VarianceQTY']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Map priority values
    df['Priority'] = df['Priority'].replace({
        '1-Normal': 'Ad-hoc Normal',
        '2-ADHOC Normal': 'Ad-hoc Normal',
        '3-ADHOC Urgent': 'Ad-hoc Urgent',
        '1-ADHOC Critical': 'Ad-hoc Critical'
    })

    # ------------------------ SIDEBAR FILTER ------------------------
    st.sidebar.header("🔍 Filter Data")

    available_dates = sorted(df['Date'].dt.date.unique())
    selected_date = st.sidebar.selectbox("Select a Date", options=available_dates)

    filtered_df = df[df['Date'].dt.date == selected_date]

    # ------------------------ METRICS ------------------------
    daily_orders_count = filtered_df['GINo'].nunique()

    status_table = filtered_df.groupby(['Priority', 'Status']).size().unstack(fill_value=0)

    weekly_summary = df.groupby(pd.Grouper(key='Date', freq='W-MON')).agg(
        Orders_Received=('GINo', 'nunique'),
        Orders_Cancelled=('Status', lambda x: (x == '98-Cancelled').sum())
    ).reset_index()

    total_lines = filtered_df.shape[0]
    back_orders = (filtered_df['Status'] == 'Back Order').sum()
    back_order_pct = (back_orders / total_lines * 100) if total_lines > 0 else 0

    shipped_lines = filtered_df['ShippedQTY'].sum()
    variance_lines = filtered_df['VarianceQTY'].sum()
    accuracy_pct = 100 - ((variance_lines / shipped_lines) * 100) if shipped_lines > 0 else 100

    # ------------------------ CSS FOR DIVIDERS ------------------------
    st.markdown("""
        <style>
        hr {
            border: none;
            height: 1px;
            background-color: #d3d3d3;
            margin: 2rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # ------------------------ HEADER ------------------------
    st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")

    # ------------------------ TOP ROW ------------------------
    col_left, col_right = st.columns([4, 2])

    with col_left:
        st.markdown("#### 📦 Daily Outbound Overview")

        col_date, col_metric = st.columns([2, 1])
        with col_date:
            st.metric(label="Date", value=selected_date.strftime('%d %b %Y'))
        with col_metric:
            st.metric(label="Daily Outbound Orders", value=daily_orders_count)

        # Orders by Priority Bar Chart
        order_types = filtered_df['Priority'].dropna().unique().tolist()
        status_categories = filtered_df['Status'].dropna().unique().tolist()
        colors = px.colors.qualitative.Set3

        bar_data = {
            status: [len(filtered_df[(filtered_df['Priority'] == p) & (filtered_df['Status'] == status)]) for p in order_types]
            for status in status_categories
        }

        bar_fig = go.Figure()
        for i, status in enumerate(status_categories):
            bar_fig.add_trace(go.Bar(
                y=order_types,
                x=bar_data[status],
                name=status,
                orientation='h',
                marker=dict(color=colors[i % len(colors)])
            ))

        bar_fig.update_layout(
            barmode='stack',
            xaxis_title='Order Count',
            margin=dict(l=10, r=10, t=30, b=30),
            height=400
        )
        st.plotly_chart(bar_fig, use_container_width=True)

    with col_right:
        st.markdown("#### 📋 Order Status Table")
        st.dataframe(status_table)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ------------------------ BOTTOM ROW ------------------------
    col_bottom_left, col_bottom_right = st.columns([3, 2])

    with col_bottom_left:
        st.markdown("#### 📊 Orders Over the Past 2 Weeks")

        fig = go.Figure(data=[
            go.Bar(name='Orders Received', x=weekly_summary['Date'], y=weekly_summary['Orders_Received'], marker_color='lightgreen'),
            go.Bar(name='Orders Cancelled', x=weekly_summary['Date'], y=weekly_summary['Orders_Cancelled'], marker_color='red')
        ])
        fig.update_layout(barmode='group', xaxis_title='Date', yaxis_title='Order Count')
        st.plotly_chart(fig, use_container_width=True)

    with col_bottom_right:
        st.markdown("#### 📈 Performance Metrics")

        def pie_chart(value, label, total_label):
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
                annotations=[
                    dict(text=f"{value:.2f}%", x=0.5, y=0.5, font_size=20, showarrow=False),
                    dict(text=total_label, x=0.5, y=0.2, font_size=12, showarrow=False)
                ]
            )
            return fig

        col_pie1, col_pie2 = st.columns(2)

        with col_pie1:
            st.markdown("**Back Order %**")
            st.plotly_chart(pie_chart(back_order_pct, "Back Order", f"{back_orders} of {total_lines} lines"), use_container_width=True)

        with col_pie2:
            st.markdown("**Order Accuracy %**")
            st.plotly_chart(pie_chart(accuracy_pct, "Accuracy", f"{variance_lines} Variance"), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.info("Please upload an Excel file to view the dashboard.")
