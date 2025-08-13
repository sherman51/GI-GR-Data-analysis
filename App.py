from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------- Streamlit Config ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ---------- Page Header ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")

# ---------- File Upload ----------
uploaded_file = st.sidebar.file_uploader("📂 Upload Excel File", type=["xlsx"])

# ---------- Date selection ----------
selected_date = st.sidebar.date_input("Select Date to View", datetime.today())

# ---------- Styling ----------
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

if uploaded_file:
    # Load and clean data
    df_raw = pd.read_excel(uploaded_file, skiprows=6)
    df_raw.columns = df_raw.columns.str.strip()
    df = df_raw.dropna(axis=1, how="all")
    df.dropna(how="all", inplace=True)

    # Parse date columns
    df['ExpDate'] = pd.to_datetime(df['ExpDate'], errors='coerce')
    df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
    df['ShippedOn'] = pd.to_datetime(df['ShippedOn'], errors='coerce')

    # Filter out rows without ExpDate
    df = df[df['ExpDate'].notna()]

    # Map order types and statuses
    priority_map = {
        '1-Normal': 'normal',
        '2-ADHOC Normal': 'Ad-hoc Normal',
        '3-ADHOC Urgent': 'Ad-hoc Urgent',
        '4-ADHOC Critical': 'Ad-hoc Critical'
    }
    df['Order Type'] = df['Priority'].map(priority_map).fillna(df['Priority'])

    status_map = {
        '65-Packed': 'Packed',
        '75-Shipped': 'Tpt Booked',
        '98-Cancelled': 'Open'
    }
    df['Order Status'] = df['Status'].map(status_map).fillna('Open')

    # Define order for rows and columns
    order_types = ['Back Orders', 'normal', 'Ad-hoc Normal', 'Ad-hoc Urgent', 'Ad-hoc Critical']
    segments = ['Tpt Booked', 'Packed', 'Picked', 'Open']

    # ---------- Top Row ----------
    col_left, col_right = st.columns([4, 2])

    with col_left:
        st.markdown("#### 📦 Daily Outbound Overview")
        col_date, col_orders, col_unique = st.columns(3)

        with col_date:
            st.metric(label="Date", value=selected_date.strftime('%d %b %Y'))

        with col_orders:
            total_orders = df[df['ExpDate'].dt.date == selected_date].shape[0]
            st.metric(label="Total Order Lines", value=total_orders)

        with col_unique:
            unique_gis_today = df[df['ExpDate'].dt.date == selected_date]['GINo'].nunique()
            st.metric(label="Unique GINo Today", value=unique_gis_today)

        # Prepare bar chart data with +1 to avoid zero for log scale
        data = {seg: [] for seg in segments}
        for ot in order_types:
            ot_df = df[(df['Order Type'] == ot) & (df['ExpDate'].dt.date == selected_date)]
            for seg in segments:
                count = (ot_df['Order Status'] == seg).sum()
                data[seg].append(count + 1)  # add 1 to avoid zero for log scale

        bar_fig = go.Figure()
        for seg, color in zip(segments, ['green', 'blue', 'yellow', 'salmon']):
            bar_fig.add_trace(go.Bar(
                y=order_types,
                x=data[seg],
                name=seg,
                orientation='h',
                marker=dict(color=color)
            ))

        bar_fig.update_layout(
            barmode='stack',
            xaxis_title='Order Count (log scale)',
            xaxis_type='log',
            margin=dict(l=10, r=10, t=30, b=30),
            height=400
        )
        st.plotly_chart(bar_fig, use_container_width=True)

    with col_right:
        st.markdown("#### 📋 Order Status Summary")

        # Swapped axes table: rows = Order Type, columns = Order Status
        df_status_table = df[df['ExpDate'].dt.date == selected_date].groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)

        df_status_table = df_status_table.reindex(index=order_types, columns=segments, fill_value=0)

        st.dataframe(df_status_table.style.format("{:,}"))

    # --- Ad-hoc KPIs and bar chart under the top row ---
    st.markdown("#### 🚨 Ad-hoc Priority Summary & Orders by GINo (Urgent & Critical)")

    adhoc_df = df[
        (df['ExpDate'].dt.date == selected_date) &
        (df['Order Type'].isin(['Ad-hoc Urgent', 'Ad-hoc Critical']))
    ]

    adhoc_urgent_count = (adhoc_df['Order Type'] == 'Ad-hoc Urgent').sum()
    adhoc_critical_count = (adhoc_df['Order Type'] == 'Ad-hoc Critical').sum()

    col_adhoc1, col_adhoc2 = st.columns(2)

    with col_adhoc1:
        st.metric(label="Ad-hoc Urgent Orders", value=adhoc_urgent_count)

    with col_adhoc2:
        st.metric(label="Ad-hoc Critical Orders", value=adhoc_critical_count)

    grouped = adhoc_df.groupby(['GINo', 'Order Type']).size().unstack(fill_value=0)

    if not grouped.empty:
        fig = go.Figure()

        if 'Ad-hoc Urgent' in grouped.columns:
            fig.add_trace(go.Bar(
                x=grouped.index,
                y=grouped['Ad-hoc Urgent'],
                name='Ad-hoc Urgent',
                marker_color='orange'
            ))

        if 'Ad-hoc Critical' in grouped.columns:
            fig.add_trace(go.Bar(
                x=grouped.index,
                y=grouped['Ad-hoc Critical'],
                name='Ad-hoc Critical',
                marker_color='crimson'
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title='GINo',
            yaxis_title='Order Count',
            height=400,
            margin=dict(l=10, r=10, t=30, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No Ad-hoc Urgent or Critical orders for the selected date.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Bottom Row ----------
    col_bottom_left, col_bottom_right = st.columns([3, 2])

    with col_bottom_left:
        st.markdown("#### 📊 Orders by Expiry Date (Past 14 Days)")
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
        fig.update_layout(barmode='group', xaxis_title='Expiry Date', yaxis_title='Order Count')
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

        # 🔄 Filter to past 14 days, excluding today and future
        today = pd.Timestamp.today().normalize()
        recent_past_df = df[
            (df['ExpDate'] < today) &
            (df['ExpDate'] >= today - pd.Timedelta(days=14))
        ]

        total_expected = recent_past_df['ExpectedQTY'].sum()
        total_shipped = recent_past_df['ShippedQTY'].sum()
        accuracy_pct = (total_shipped / total_expected * 100) if total_expected else 0

        total_variance = recent_past_df['VarianceQTY'].sum()
        backorder_pct = (total_variance / total_expected * 100) if total_expected else 0

        col_pie1, col_pie2 = st.columns(2)

        with col_pie1:
            st.markdown("**Back Order %**")
            fig_back_order = pie_chart(backorder_pct, "Back Order", f"{int(total_variance)} Variance")
            st.plotly_chart(fig_back_order, use_container_width=True)

        with col_pie2:
            st.markdown("**Order Accuracy %**")
            missed = total_expected - total_shipped
            fig_order_accuracy = pie_chart(accuracy_pct, "Accuracy", f"{int(missed)} Missed")
            st.plotly_chart(fig_order_accuracy, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Footer ----------
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.warning("📄 Please upload an Excel file to begin.")
