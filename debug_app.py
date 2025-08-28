#!/usr/bin/env python3
"""
Debug version of the chatbot app to identify display issues
"""

import streamlit as st
import pandas as pd
import duckdb
import logging
import os
from datetime import datetime
from typing import Optional

# Import our custom modules
import llm_adapter
import sql_guard
import viz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="🔍 デバッグ版 - NL→SQL 売上分析チャットボット",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 デバッグ版 - NL→SQL 売上分析チャットボット")
st.markdown("**このバージョンは詳細なデバッグ情報を表示します**")

# Force MockLLMAdapter
os.environ.pop('OPENAI_API_KEY', None)
os.environ.pop('ANTHROPIC_API_KEY', None)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'con' not in st.session_state:
    st.session_state.con = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

@st.cache_data
def load_and_setup_data():
    """Load data and return necessary objects"""
    # Load CSV data
    df = pd.read_csv('data/sample_sales.csv')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Setup DuckDB
    con = duckdb.connect(':memory:')
    con.register('sales', df)
    con.execute("""
        CREATE VIEW sales_with_month AS
        SELECT *, date_trunc('month', CAST(date AS TIMESTAMP)) as month
        FROM sales
    """)
    
    # Generate schema
    schema_lines = ["CREATE TABLE sales ("]
    for col, dtype in df.dtypes.items():
        if dtype == 'datetime64[ns]':
            sql_type = 'TIMESTAMP'
        elif dtype in ['int64', 'int32']:
            sql_type = 'INTEGER'
        elif dtype in ['float64', 'float32']:
            sql_type = 'DOUBLE'
        else:
            sql_type = 'TEXT'
        schema_lines.append(f"  {col} {sql_type},")
    
    schema_lines[-1] = schema_lines[-1].rstrip(',')
    schema_lines.append(");")
    schema_info = '\n'.join(schema_lines)
    
    return df, con, schema_info

# Load data
if not st.session_state.data_loaded:
    with st.spinner("データ読み込み中..."):
        df, con, schema_info = load_and_setup_data()
        st.session_state.con = con
        st.session_state.schema_info = schema_info
        st.session_state.data_loaded = True
        st.success(f"✅ データ読み込み完了: {len(df)}行")

# Debug info
with st.expander("🔧 デバッグ情報"):
    st.write("**環境変数:**")
    st.write(f"- OPENAI_API_KEY: {'設定済み' if os.getenv('OPENAI_API_KEY') else '未設定'}")
    st.write(f"- ANTHROPIC_API_KEY: {'設定済み' if os.getenv('ANTHROPIC_API_KEY') else '未設定'}")
    
    st.write("**データ情報:**")
    if st.session_state.data_loaded:
        test_query = "SELECT region, COUNT(*) as count FROM sales GROUP BY region ORDER BY region"
        result = st.session_state.con.execute(test_query).df()
        st.dataframe(result)

# Test buttons
st.subheader("🧪 テストボタン")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("北部地域の売上", key="test_north"):
        st.write("**🔍 詳細デバッグ: 北部地域の売上**")
        
        question = "北部地域の売上"
        
        # Step 1: SQL生成
        st.write("**Step 1: SQL生成**")
        try:
            raw_sql = llm_adapter.generate_sql(question, st.session_state.schema_info)
            st.code(f"生成されたSQL:\n{raw_sql}")
            
            # Step 2: SQL検証
            st.write("**Step 2: SQL検証**")
            try:
                safe_sql = sql_guard.sanitize_sql(raw_sql)
                st.success("✅ SQL検証通過")
                sql_to_use = safe_sql
            except Exception as e:
                st.warning(f"⚠️ SQL検証失敗: {e}")
                fallback_sql = sql_guard.get_fallback_query(question)
                st.code(f"フォールバックSQL:\n{fallback_sql}")
                sql_to_use = fallback_sql
            
            # Step 3: SQL実行
            st.write("**Step 3: SQL実行**")
            try:
                result_df = st.session_state.con.execute(sql_to_use.strip()).df()
                st.success(f"✅ SQL実行成功: {len(result_df)}行取得")
                
                if not result_df.empty:
                    st.write("**Step 4: 結果表示**")
                    st.dataframe(result_df)
                    
                    # 売上の確認
                    if 'total_revenue' in result_df.columns:
                        total = result_df['total_revenue'].iloc[0]
                        st.metric("北部地域売上", f"{total:,.0f}円")
                    
                    st.write("**Step 5: 可視化**")
                    viz.auto_visualize(result_df)
                    
                    st.write("**Step 6: 要約**")
                    try:
                        summary = llm_adapter.summarize(sql_to_use, result_df.head(5).to_string())
                        st.write(summary)
                    except Exception as e:
                        st.warning(f"要約生成失敗: {e}")
                    
                    st.write("**Step 7: CSVダウンロード**")
                    csv_data = result_df.to_csv(index=False).encode('utf-8')
                    st.download_button("結果をダウンロード", csv_data, "north_sales.csv", "text/csv")
                    
                else:
                    st.error("❌ 結果が空です")
                    
            except Exception as e:
                st.error(f"❌ SQL実行エラー: {e}")
                
        except Exception as e:
            st.error(f"❌ SQL生成エラー: {e}")

with col2:
    if st.button("全地域の売上", key="test_all"):
        st.write("**🔍 比較用: 全地域の売上**")
        
        query = "SELECT region, SUM(revenue) as total_revenue FROM sales GROUP BY region ORDER BY total_revenue DESC"
        try:
            result = st.session_state.con.execute(query).df()
            st.dataframe(result)
            
            # 北部を強調
            north_row = result[result['region'] == 'North']
            if not north_row.empty:
                north_revenue = north_row['total_revenue'].iloc[0]
                st.success(f"✅ North地域確認: {north_revenue:,.0f}円")
            else:
                st.error("❌ North地域が見つかりません")
                
        except Exception as e:
            st.error(f"❌ エラー: {e}")

with col3:
    if st.button("MockLLMテスト", key="test_mock"):
        st.write("**🔍 MockLLMAdapter動作確認**")
        
        # MockLLMAdapter の直接テスト
        mock_adapter = llm_adapter.MockLLMAdapter()
        
        test_questions = ["北部地域の売上", "北部の売上", "North sales"]
        for q in test_questions:
            sql = mock_adapter.generate_sql(q, st.session_state.schema_info)
            st.code(f"質問: {q}\n生成SQL: {sql}")

# Regular chat interface
st.subheader("💬 通常のチャット")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("質問を入力してください"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        st.write(f"**処理中: {prompt}**")
        
        try:
            # SQL生成
            raw_sql = llm_adapter.generate_sql(prompt, st.session_state.schema_info)
            st.write(f"生成SQL: `{raw_sql}`")
            
            # 検証・実行
            try:
                safe_sql = sql_guard.sanitize_sql(raw_sql)
            except:
                safe_sql = sql_guard.get_fallback_query(prompt)
                st.warning("フォールバック使用")
            
            result_df = st.session_state.con.execute(safe_sql.strip()).df()
            
            if not result_df.empty:
                st.dataframe(result_df)
                viz.auto_visualize(result_df)
                
                # 要約
                try:
                    summary = llm_adapter.summarize(safe_sql, result_df.head(5).to_string())
                    st.write(summary)
                except:
                    st.write("分析完了")
                
                # CSV
                csv_data = result_df.to_csv(index=False).encode('utf-8')
                st.download_button("CSV保存", csv_data, "result.csv", "text/csv")
            else:
                st.warning("結果なし")
                
        except Exception as e:
            st.error(f"エラー: {e}")
    
    st.session_state.messages.append({"role": "assistant", "content": f"質問「{prompt}」を処理しました。"})