#!/usr/bin/env python3
"""
Minimal test to verify the specific issue with 北部地域の売上
"""
import streamlit as st
import pandas as pd
import duckdb
import llm_adapter
import sql_guard

# Force MockLLMAdapter by clearing keys
import os
os.environ.pop('OPENAI_API_KEY', None)
os.environ.pop('ANTHROPIC_API_KEY', None)

st.title("🔍 北部地域売上テスト")

@st.cache_data
def setup_data():
    df = pd.read_csv('data/sample_sales.csv')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    con = duckdb.connect(':memory:')
    con.register('sales', df)
    con.execute("""
        CREATE VIEW sales_with_month AS
        SELECT *, date_trunc('month', CAST(date AS TIMESTAMP)) as month
        FROM sales
    """)
    
    schema_info = """CREATE TABLE sales (
      date TIMESTAMP,
      category TEXT,
      units INTEGER,
      unit_price INTEGER,
      region TEXT,
      sales_channel TEXT,
      customer_segment TEXT,
      revenue DOUBLE
    );
    -- Helper view: sales_with_month has all columns plus month."""
    
    return df, con, schema_info

df, con, schema_info = setup_data()

st.write(f"✅ データ読み込み: {len(df)}行")

# Test specific query
question = "北部地域の売上"
st.subheader(f"テスト質問: {question}")

# Step 1: SQL generation
st.write("**Step 1: SQL生成**")
sql = llm_adapter.generate_sql(question, schema_info)
st.code(sql)

# Step 2: SQL validation
st.write("**Step 2: SQL検証**")
try:
    safe_sql = sql_guard.sanitize_sql(sql)
    st.success("✅ SQL検証通過")
except Exception as e:
    st.error(f"❌ SQL検証失敗: {e}")
    safe_sql = sql_guard.get_fallback_query(question)
    st.code(f"フォールバック: {safe_sql}")

# Step 3: SQL実行
st.write("**Step 3: SQL実行**")
try:
    result_df = con.execute(safe_sql).df()
    st.success(f"✅ 実行成功: {len(result_df)}行")
    if not result_df.empty:
        st.dataframe(result_df)
        
        # 詳細表示
        if 'total_revenue' in result_df.columns:
            revenue = result_df['total_revenue'].iloc[0]
            st.metric("北部地域売上", f"{revenue:,.0f}円")
    else:
        st.error("❌ 結果が空")
        
except Exception as e:
    st.error(f"❌ SQL実行エラー: {e}")

# Debug info
st.subheader("🔧 デバッグ情報")
st.write("**地域データ確認:**")
regions_query = "SELECT region, COUNT(*) as count, SUM(revenue) as total FROM sales GROUP BY region ORDER BY region"
regions_result = con.execute(regions_query).df()
st.dataframe(regions_result)