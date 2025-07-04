import streamlit as st
import pandas as pd

st.title('販売データ分析アプリ')
st.write('Pandasを使ってCSVファイルを読み込み、表示してみましょう！')

# CSVファイルを読み込む
df = pd.read_csv('data/sample_sales.csv')

# 読み込んだデータの最初の5行を表示する
st.subheader('データの最初の5行')
st.dataframe(df.head())

# 各列の統計情報を確認する
st.subheader('各列の統計情報')
st.dataframe(df.describe())

st.write('---')
st.write('これで、Pandasを使ってCSVファイルを読み込み、Streamlitで表示することができましたね！')