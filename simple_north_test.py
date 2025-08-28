#!/usr/bin/env python3
"""
Simple test for North region issue
"""
import streamlit as st
import pandas as pd
import duckdb
import llm_adapter
import sql_guard
import os

# Clear API keys
os.environ.pop('OPENAI_API_KEY', None)
os.environ.pop('ANTHROPIC_API_KEY', None)

st.title("🔍 簡単テスト：北部地域")

@st.cache_data
def setup_data():
    df = pd.read_csv('data/sample_sales.csv')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    con = duckdb.connect(':memory:')
    con.register('sales', df)
    schema_info = """CREATE TABLE sales (date TIMESTAMP, category TEXT, units INTEGER, unit_price INTEGER, region TEXT, sales_channel TEXT, customer_segment TEXT, revenue DOUBLE);"""
    return df, con, schema_info

df, con, schema_info = setup_data()

st.write(f"データ行数: {len(df)}")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Show current messages
st.write("**現在のメッセージ履歴:**")
for i, msg in enumerate(st.session_state.messages):
    st.write(f"{i+1}. [{msg['role']}] {msg['content'][:100]}...")

# Direct test button
if st.button("「北部地域の売上」をテスト"):
    question = "北部地域の売上"
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    st.write(f"✅ ユーザーメッセージ追加: {question}")
    
    # Generate SQL
    try:
        sql = llm_adapter.generate_sql(question, schema_info)
        st.write(f"✅ SQL生成: {sql}")
        
        # Execute SQL
        result_df = con.execute(sql).df()
        st.write(f"✅ SQL実行: {len(result_df)}行")
        
        if not result_df.empty:
            st.dataframe(result_df)
            revenue = result_df['total_revenue'].iloc[0]
            st.success(f"北部地域売上: {revenue:,.0f}円")
            
            # Add assistant message  
            response = f"クエリを実行し、{len(result_df)}行の結果を取得しました。北部地域の売上は{revenue:,.0f}円です。"
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.write(f"✅ アシスタントメッセージ追加")
            
        else:
            st.error("❌ 結果が空")
            st.session_state.messages.append({"role": "assistant", "content": "結果が空でした"})
            
    except Exception as e:
        st.error(f"❌ エラー: {e}")
        st.session_state.messages.append({"role": "assistant", "content": f"エラー: {e}"})
    
    # Force refresh
    st.rerun()

# Manual message display
st.write("**手動メッセージ表示:**")
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])