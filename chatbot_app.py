import streamlit as st
import pandas as pd
import duckdb
import logging
import os
from datetime import datetime
from typing import Optional
from io import StringIO

# Import our custom modules
import llm_adapter
import sql_guard
import viz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATA_FILE = "data/sample_sales.csv"
MAX_ROWS = 5000

# Page configuration
st.set_page_config(
    page_title="NL→SQL 売上分析チャットボット",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'con' not in st.session_state:
    st.session_state.con = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'schema_info' not in st.session_state:
    st.session_state.schema_info = ""


def load_data() -> tuple[pd.DataFrame, str]:
    """Load CSV data and return DataFrame and schema info"""
    try:
        # Load CSV data
        df = pd.read_csv(DATA_FILE)
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Generate schema information for LLM
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
        
        schema_lines[-1] = schema_lines[-1].rstrip(',')  # Remove last comma
        schema_lines.append(");")
        schema_lines.append("-- Helper view: sales_with_month has all columns plus 'month' (first day of month).")
        
        schema_info = '\n'.join(schema_lines)
        
        logger.info(f"Data loaded successfully: {len(df)} rows, {len(df.columns)} columns")
        return df, schema_info
        
    except FileNotFoundError:
        st.error(f"データファイルが見つかりません: {DATA_FILE}")
        return None, ""
    except Exception as e:
        st.error(f"データ読み込みエラー: {str(e)}")
        logger.error(f"Error loading data: {e}")
        return None, ""


def setup_database(df: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    """Setup DuckDB connection and create tables/views"""
    try:
        # Create DuckDB connection
        con = duckdb.connect(':memory:')
        
        # Register DataFrame as table
        con.register('sales', df)
        
        # Create helper view with month column
        con.execute("""
            CREATE VIEW sales_with_month AS
            SELECT *, 
                   date_trunc('month', CAST(date AS TIMESTAMP)) as month
            FROM sales
        """)
        
        logger.info("Database setup completed successfully")
        return con
        
    except Exception as e:
        st.error(f"データベース設定エラー: {str(e)}")
        logger.error(f"Database setup error: {e}")
        return None


def display_sidebar_summary(df: pd.DataFrame):
    """Display data summary and sample questions in sidebar"""
    with st.sidebar:
        st.title("📊 データ概要")
        
        # Basic statistics
        st.metric("データ期間", f"{df['date'].min().strftime('%Y-%m-%d')} - {df['date'].max().strftime('%Y-%m-%d')}")
        st.metric("総レコード数", f"{len(df):,}")
        
        # Categories
        if 'category' in df.columns:
            categories = df['category'].unique()
            with st.expander("カテゴリ一覧"):
                for cat in categories[:10]:  # Show first 10
                    st.write(f"• {cat}")
                if len(categories) > 10:
                    st.write(f"...他{len(categories)-10}件")
        
        # Regions
        if 'region' in df.columns:
            regions = df['region'].unique()
            with st.expander("地域一覧"):
                for region in regions:
                    st.write(f"• {region}")
        
        # Sales channels
        if 'sales_channel' in df.columns:
            channels = df['sales_channel'].unique()
            with st.expander("販売チャネル"):
                for channel in channels:
                    st.write(f"• {channel}")
        
        # Customer segments
        if 'customer_segment' in df.columns:
            segments = df['customer_segment'].unique()
            with st.expander("顧客セグメント"):
                for segment in segments:
                    st.write(f"• {segment}")
        
        st.divider()
        
        # Sample questions with direct execution
        st.subheader("💡 サンプル質問")
        
        sample_questions = [
            "北部地域の売上",
            "月毎のカテゴリー別の売上",
            "チャネルごとの売上", 
            "地域ごとの売上の合計",
            "2025年1月の売上トップ5カテゴリ",
            "オンラインと店舗の売上比較"
        ]
        
        for question in sample_questions:
            if st.button(question, key=f"sample_{question}", use_container_width=True):
                # Directly handle the question
                process_and_store_question(question)
                st.rerun()  # Force refresh to show the result


def process_and_store_question(question: str):
    """Process a question and store the complete response in session state"""
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": question})
    
    # Debug logging
    logger.info(f"Processing question: {question}")
    
    # Process assistant response (no immediate display)
    try:
        # Step 1: Generate SQL
        sql = None
        try:
            raw_sql = llm_adapter.generate_sql(question, st.session_state.schema_info)
            logger.info(f"Generated raw SQL: {raw_sql}")
            sql = sql_guard.sanitize_sql(raw_sql)
            logger.info(f"Sanitized SQL: {sql}")
        except Exception as e:
            logger.warning(f"SQL generation failed, using fallback: {e}")
            sql = sql_guard.get_fallback_query(question)
            logger.info(f"Fallback SQL: {sql}")
        
        # Step 2: Execute SQL and get results
        result_df = None
        try:
            result_df = st.session_state.con.execute(sql).df()
            logger.info(f"SQL execution result: {len(result_df)} rows")
            
            if result_df.empty:
                logger.warning("Query result is empty")
                st.session_state.messages.append({"role": "assistant", "content": "クエリの結果が空でした。"})
                return
            else:
                logger.info(f"Result data: {result_df.to_dict()}")
                
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            st.session_state.messages.append({"role": "assistant", "content": f"SQL実行エラー: {str(e)}"})
            return
            
        # Add comprehensive assistant response to history with embedded data
        response_parts = [
            f"**生成SQL:**\n```sql\n{sql}\n```",
            f"**結果:** {len(result_df)}行のデータを取得",
        ]
        
        # Add summary if available  
        try:
            data_preview = result_df.head(3).to_string()
            summary = llm_adapter.summarize(sql, data_preview)
            response_parts.append(f"**分析結果:** {summary}")
        except:
            pass
            
        response_content = "\n\n".join(response_parts)
        
        # Store message with data for visualization
        message_data = {
            "role": "assistant", 
            "content": response_content, 
            "has_data": True,
            "result_df": result_df.to_dict(),  # Store as dict to avoid pickle issues
            "sql": sql
        }
        st.session_state.messages.append(message_data)
        
    except Exception as e:
        # Fatal error handling
        logger.error(f"Fatal error in process_and_store_question: {e}")
        st.session_state.messages.append({"role": "assistant", "content": f"エラー: {str(e)}"})




def main():
    """Main application function"""
    
    # Title and description
    st.title("📊 NL→SQL 売上分析チャットボット")
    st.markdown("""
    自然言語で売上データに関する質問をすると、自動的にSQLクエリを生成して結果を可視化します。  
    サイドバーのサンプル質問をクリックするか、下の入力欄に質問を入力してください。
    """)
    
    # Initialize data if not already loaded
    if not st.session_state.data_loaded:
        with st.spinner("データを読み込み中..."):
            df, schema_info = load_data()
            
            if df is not None:
                con = setup_database(df)
                if con is not None:
                    st.session_state.con = con
                    st.session_state.schema_info = schema_info
                    st.session_state.data_loaded = True
                    
                    # Display sidebar summary
                    display_sidebar_summary(df)
                    
                    st.success("✅ データの読み込みが完了しました！")
                else:
                    st.stop()
            else:
                st.stop()
    else:
        # Data already loaded, just display sidebar
        df, _ = load_data()  # Reload for sidebar display
        if df is not None:
            display_sidebar_summary(df)
    
    # Check for LLM configuration
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('ANTHROPIC_API_KEY'):
        st.warning("""
        ⚠️ APIキーが設定されていません。  
        環境変数 `OPENAI_API_KEY` または `ANTHROPIC_API_KEY` を設定してください。  
        APIキーがない場合でも、フォールバッククエリで基本的な分析は実行できます。
        """)
    
    # Chat input
    if prompt := st.chat_input("例: 月毎のカテゴリー別の売上を教えて"):
        process_and_store_question(prompt)
        st.rerun()  # Refresh to show updated history
    
    # Display chat history
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # If this is an assistant message with data, show table and graph
            if (message["role"] == "assistant" and message.get("has_data", False)):
                try:
                    # Reconstruct DataFrame from stored dict
                    result_df = pd.DataFrame.from_dict(message["result_df"])
                    
                    # Display data table
                    st.dataframe(result_df, use_container_width=True)
                    
                    # Display visualization
                    try:
                        import viz
                        viz.auto_visualize(result_df)
                    except Exception as e:
                        st.warning(f"グラフの表示に失敗しました: {e}")
                    
                    # CSV Download button
                    csv_data = result_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="結果をCSVで保存",
                        data=csv_data,
                        file_name="result.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key=f"download_{i}"  # Unique key for each download button
                    )
                except Exception as e:
                    st.warning(f"データの表示に失敗しました: {e}")


if __name__ == "__main__":
    main()