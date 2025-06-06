import streamlit as st
import pandas as pd

DATA_PATH = "data/sample_sales.csv"

st.set_page_config(page_title="Simple Sales Dashboard", layout="centered")

# タイトル
st.title("🛒 Sample Sales Dashboard")

# データ読み込み
@st.cache_data
def load_data(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df["sales"] = df["units"] * df["unit_price"]
    return df

df = load_data(DATA_PATH)

st.subheader("Raw Data")
st.dataframe(df, use_container_width=True)

# 日付範囲フィルタ
st.sidebar.header("Filters")
min_date, max_date = df["date"].min(), df["date"].max()
start, end = st.sidebar.date_input("Date range", (min_date, max_date))
mask = (df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))
filtered = df.loc[mask]

# 集計
summary = (
    filtered.groupby("category")["sales"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)

st.subheader("Sales by Category")
st.bar_chart(summary, x="category", y="sales")

st.subheader("Daily Sales Trend")
daily = filtered.groupby("date")["sales"].sum().reset_index()
st.line_chart(daily, x="date", y="sales")

st.caption("Customize this code to fit your own CSV structure!")
