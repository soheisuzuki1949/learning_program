#!/usr/bin/env python3
"""
Graph display test
"""
import streamlit as st
import pandas as pd
import duckdb
import llm_adapter
import sql_guard
import viz
import os

# Force MockLLMAdapter
os.environ.pop('OPENAI_API_KEY', None)
os.environ.pop('ANTHROPIC_API_KEY', None)

st.title("📊 グラフ表示テスト")

# Setup data
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

st.write("✅ データセットアップ完了")

# Test different queries
test_queries = [
    ("北部地域の売上", "地域別の棒グラフが表示されるはず"),
    ("地域ごとの売上の合計", "全地域の棒グラフが表示されるはず"), 
    ("チャネルごとの売上", "チャネル別の棒グラフが表示されるはず"),
    ("月毎のカテゴリー別の売上", "月次トレンドの線グラフが表示されるはず")
]

for question, expected in test_queries:
    if st.button(f"テスト: {question}"):
        st.write(f"**質問:** {question}")
        st.write(f"**期待結果:** {expected}")
        
        try:
            # Generate and execute SQL
            sql = llm_adapter.generate_sql(question, schema_info)
            safe_sql = sql_guard.sanitize_sql(sql)
            result_df = con.execute(safe_sql).df()
            
            st.code(sql, language='sql')
            st.success(f"✅ {len(result_df)}行のデータを取得")
            
            if not result_df.empty:
                st.write("**データテーブル:**")
                st.dataframe(result_df, use_container_width=True)
                
                st.write("**グラフ:**")
                try:
                    viz.auto_visualize(result_df)
                    st.success("✅ グラフ表示成功")
                except Exception as e:
                    st.error(f"❌ グラフ表示失敗: {e}")
            else:
                st.error("❌ データが空")
                
        except Exception as e:
            st.error(f"❌ エラー: {e}")
        
        st.divider()