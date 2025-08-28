# viz.py
import pandas as pd
import plotly.express as px
import streamlit as st


def _coerce_numeric(s):
    if pd.api.types.is_numeric_dtype(s):
        return s
    try:
        return pd.to_numeric(s, errors="coerce").fillna(0)
    except Exception:
        return s


def auto_visualize(df):
    if df is None or len(df) == 0:
        st.info("該当データがありません。")
        return

    # month を datetime に（あれば）
    if "month" in df.columns:
        try:
            df = df.copy()
            df["month"] = pd.to_datetime(df["month"], errors="coerce")
            df = df.sort_values("month")
        except Exception:
            pass

    # 次元候補
    dims = [c for c in ["category", "region", "sales_channel", "customer_segment"] if c in df.columns]
    dim = dims[0] if dims else None

    # 値候補
    preferred = ["total_revenue", "revenue", "units", "unit_price"]
    val = next((c for c in preferred if c in df.columns), None)
    if val is None:
        # 任意の数値列
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                val = c; break
    if val is None:
        # 数値に変換できる文字列列を探す
        for c in df.columns:
            coerced = _coerce_numeric(df[c])
            if pd.api.types.is_numeric_dtype(coerced):
                df = df.copy(); df[c] = coerced; val = c; break

    if val is None:
        st.warning("数値列が見つからず、グラフを描画できませんでした。")
        return

    try:
        if "month" in df.columns:
            fig = px.line(df, x="month", y=val, color=dim, markers=True)
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), title=f"{(dim or 'all')} × {val}")
            st.plotly_chart(fig, use_container_width=True)
            return

        # 棒グラフ
        xcol = dim if dim else df.reset_index().columns[0]
        plot_df = df.copy()
        if dim is None:
            plot_df = plot_df.reset_index()
        # x が非文字列ならキャスト
        plot_df[xcol] = plot_df[xcol].astype(str)
        plot_df[val] = _coerce_numeric(plot_df[val])
        fig = px.bar(plot_df, x=xcol, y=val)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), title=f"{xcol} × {val}")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"グラフ描画に失敗しました: {e}")


# Legacy functions for backward compatibility (if needed elsewhere)
def format_number(num) -> str:
    """Format number with comma separators"""
    if pd.isna(num):
        return 'N/A'
    if isinstance(num, (int, float)):
        return f"{num:,}"
    return str(num)


def display_data_table(df: pd.DataFrame) -> None:
    """
    Display DataFrame as a formatted table in Streamlit
    
    Args:
        df: DataFrame to display
    """
    if df.empty:
        st.warning("クエリの結果が空です。")
        return
    
    # Format numeric columns
    df_display = df.copy()
    
    for col in df_display.columns:
        if df_display[col].dtype in ['int64', 'float64']:
            df_display[col] = df_display[col].apply(format_number)
    
    # Display with custom styling
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )
    
    # Show data summary
    st.caption(f"表示データ: {len(df)} 行, {len(df.columns)} 列")