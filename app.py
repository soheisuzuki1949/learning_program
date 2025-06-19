import pandas as pd
import streamlit as st
from datetime import datetime

# --------------------------------------------------
# ページ設定
# --------------------------------------------------
st.set_page_config(page_title="Sample Sales Dashboard", page_icon="📊", layout="wide")

# --------------------------------------------------
# データ読み込み
# --------------------------------------------------
df = pd.read_csv("data/sample_sales.csv", parse_dates=["date"])

# --------------------------------------------------
# サイドバー ― フィルター類
# --------------------------------------------------
st.sidebar.header("🔧 フィルター")

# 日付スライダー（pandas.Timestamp → datetime 変換）
min_date = df["date"].min().to_pydatetime()
max_date = df["date"].max().to_pydatetime()
date_range = st.sidebar.slider(
    "期間を選択",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD",
)

# マルチセレクト
cats = st.sidebar.multiselect(
    "カテゴリ",
    options=df["category"].unique().tolist(),
    default=df["category"].unique().tolist(),
)
regions = st.sidebar.multiselect(
    "地域",
    options=df["region"].unique().tolist(),
    default=df["region"].unique().tolist(),
)
channels = st.sidebar.multiselect(
    "チャネル",
    options=df["sales_channel"].unique().tolist(),
    default=df["sales_channel"].unique().tolist(),
)

# チャートタイプ切替
chart_type = st.sidebar.radio("チャートタイプ", ["Line", "Bar"], horizontal=True)

# --------------------------------------------------
# フィルタリング
# --------------------------------------------------
start_dt = pd.to_datetime(date_range[0])
end_dt   = pd.to_datetime(date_range[1])

df_filt = df[
    (df["date"].between(start_dt, end_dt))
    & (df["category"].isin(cats))
    & (df["region"].isin(regions))
    & (df["sales_channel"].isin(channels))
]

# --------------------------------------------------
# KPI ― 主要指標
# --------------------------------------------------
st.title("📊 Sample Sales Dashboard")
total_revenue   = int(df_filt["revenue"].sum())
total_units     = int(df_filt["units"].sum())
avg_unit_price  = int(df_filt["unit_price"].mean()) if not df_filt.empty else 0

col1, col2, col3 = st.columns(3)
col1.metric("売上合計 (円)", f"{total_revenue:,.0f}")
col2.metric("販売数量 (個)", f"{total_units:,}")
col3.metric("平均単価 (円)", f"{avg_unit_price:,.0f}")

st.divider()

# --------------------------------------------------
# タブ ― 可視化 & データ
# --------------------------------------------------
tab1, tab2 = st.tabs(["📈 可視化", "📄 データ"])

with tab1:
    # 日別売上推移
    st.subheader("🗓️ 日別売上推移")
    revenue_daily = (
        df_filt.groupby("date", as_index=False)["revenue"].sum().sort_values("date")
    )
    if chart_type == "Line":
        st.line_chart(revenue_daily, x="date", y="revenue", height=300)
    else:
        st.bar_chart(revenue_daily, x="date", y="revenue", height=300)

    # カテゴリ別売上
    st.subheader("🏷️ カテゴリ別売上")
    revenue_by_cat = (
        df_filt.groupby("category", as_index=False)["revenue"].sum().sort_values("revenue")
    )
    st.bar_chart(revenue_by_cat, x="category", y="revenue", height=300)

    # 地域別売上
    st.subheader("🌎 地域別売上")
    revenue_by_region = (
        df_filt.groupby("region", as_index=False)["revenue"].sum().sort_values("revenue")
    )
    st.bar_chart(revenue_by_region, x="region", y="revenue", height=300)

with tab2:
    st.subheader("フィルタ後データ")
    st.dataframe(df_filt.reset_index(drop=True), use_container_width=True)
    csv = df_filt.to_csv(index=False).encode("utf-8")
    st.download_button("📥 CSV ダウンロード", csv, "filtered_sales.csv", "text/csv")
