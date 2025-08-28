#!/usr/bin/env python3
"""
Direct test for the specific "北部地域の売上" issue
"""
import streamlit as st
import pandas as pd
import duckdb
import llm_adapter
import sql_guard
import os

# Force MockLLMAdapter
os.environ.pop('OPENAI_API_KEY', None)
os.environ.pop('ANTHROPIC_API_KEY', None)

st.title("🔍 直接テスト：北部地域の売上")

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

# 問題の質問を直接テスト
question = "北部地域の売上"

if st.button("「北部地域の売上」をテスト"):
    st.write(f"**質問:** {question}")
    
    # 現在のチャットボットアプリと同じ処理フロー
    try:
        # Step 1: Generate SQL
        st.write("**Step 1: SQL生成**")
        try:
            raw_sql = llm_adapter.generate_sql(question, schema_info)
            sql = sql_guard.sanitize_sql(raw_sql)
            st.success(f"✅ SQL生成成功")
            st.code(sql, language='sql')
        except Exception as e:
            st.warning(f"⚠️ SQL生成でフォールバック使用: {e}")
            sql = sql_guard.get_fallback_query(question)
            st.code(sql, language='sql')
        
        # Step 2: Execute SQL
        st.write("**Step 2: SQL実行**") 
        try:
            result_df = con.execute(sql).df()
            
            if result_df.empty:
                st.error("❌ 結果が空です")
            else:
                st.success(f"✅ SQL実行成功: {len(result_df)}行")
                
                # Step 3: Display results
                st.write("**Step 3: 結果表示**")
                st.dataframe(result_df, use_container_width=True)
                
                # Specific revenue display
                if 'total_revenue' in result_df.columns:
                    revenue = result_df['total_revenue'].iloc[0] 
                    region = result_df['region'].iloc[0]
                    st.metric(f"{region}地域売上", f"{revenue:,.0f}円")
                    st.balloons()
                
                # Step 4: Summary
                st.write("**Step 4: 要約**")
                try:
                    data_preview = result_df.head(3).to_string()
                    summary = llm_adapter.summarize(sql, data_preview)
                    st.write(summary)
                except Exception as e:
                    st.warning(f"要約生成失敗: {e}")
                    
        except Exception as e:
            st.error(f"❌ SQL実行エラー: {e}")
            st.write(f"エラー詳細: {str(e)}")
            
    except Exception as e:
        st.error(f"❌ 全体エラー: {e}")
        st.write(f"エラー詳細: {str(e)}")

# Raw data check
st.divider()
st.subheader("🔧 データ確認")

if st.button("全地域データを表示"):
    all_regions = con.execute("SELECT region, COUNT(*) as count, SUM(revenue) as total FROM sales GROUP BY region ORDER BY region").df()
    st.dataframe(all_regions)
    
    # 北部地域の確認
    north_data = all_regions[all_regions['region'] == 'North']
    if not north_data.empty:
        st.success(f"✅ North地域確認: {north_data['total'].iloc[0]:,.0f}円 ({north_data['count'].iloc[0]}件)")
    else:
        st.error("❌ North地域がデータにありません")