import streamlit as st
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import seaborn as sns

uploaded_file = st.sidebar.file_uploader("Choose an XLSX file", type=['xlsx'])


# Daily Order breakdown


# --------------------
# Load and prepare data
# --------------------
file_path = "GI SKU line.xlsx"  # Change if file path differs
df = pd.read_excel(file_path, sheet_name="Orders")

# If date is already selected, we assume df is already filtered externally.
# Otherwise, you could filter here with something like:
# df = df[df["CreatedOn"].dt.date == selected_date]

# --------------------
# Count orders by Priority & Status
# --------------------
orders_by_priority_status = (
    df.groupby(["Priority", "Status"])
    .size()
    .reset_index(name="OrderCount")
)

# Create cross-matrix (status as rows, priority as columns)
cross_matrix = pd.pivot_table(
    orders_by_priority_status,
    index="Status",
    columns="Priority",
    values="OrderCount",
    aggfunc="sum",
    fill_value=0
)

# --------------------
# Create figure layout
# --------------------
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(14, 6),
    gridspec_kw={"width_ratios": [2, 1]}
)

# --- Left: Stacked Horizontal Bar Chart ---
pivot_bar = orders_by_priority_status.pivot(
    index="Priority", columns="Status", values="OrderCount"
).fillna(0)

# Ensure consistent priority order
pivot_bar = pivot_bar.reindex(index=sorted(pivot_bar.index))

bottom_vals = None
for status in pivot_bar.columns:
    ax1.barh(pivot_bar.index, pivot_bar[status], left=bottom_vals, label=status)
    if bottom_vals is None:
        bottom_vals = pivot_bar[status].copy()
    else:
        bottom_vals += pivot_bar[status]

ax1.set_xlabel("Number of Orders")
ax1.set_ylabel("Order Priority")
ax1.set_title("Outbound Orders by Priority & Status")
ax1.legend(title="Status")

# --- Right: Cross-Matrix Heatmap ---
sns.heatmap(
    cross_matrix,
    annot=True,
    fmt="d",
    cmap="Blues",
    cbar=False,
    ax=ax2
)
ax2.set_title("Status vs Priority (Order Count)")
ax2.set_xlabel("Order Priority")
ax2.set_ylabel("Status")

plt.tight_layout()
plt.show()




