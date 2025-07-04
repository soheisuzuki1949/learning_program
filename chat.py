import streamlit as st
from openai import OpenAI # OpenAIの機能を使うために必要です

# OpenAIのクライアントを初期化します
# ここで環境変数に設定したAPIキーを自動的に読み込みます
client = OpenAI()

# アプリのタイトルを設定します
st.title('シンプルなAIチャットボット')

# チャット履歴を保存するための場所を用意します
# もし履歴がなければ、最初のメッセージを設定します
if "messages" not in st.session_state:
    st.session_state.messages = []

# これまでのチャット履歴を表示します
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからの新しいメッセージを受け取る入力欄を表示します
if prompt := st.chat_input("何か質問してください..."):
    # ユーザーのメッセージを履歴に追加して表示します
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AIに応答を生成してもらう部分です
    with st.chat_message("assistant"):
        # プロンプト（指示）をOpenAIのモデルに送ります
        # gpt-4oは現在最も高性能なモデルです
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True, # AIが文章を生成するのをリアルタイムで表示するための設定です
        )
        # AIからの応答を少しずつ表示します
        response = st.write_stream(stream)
    # AIの応答を履歴に追加します
    st.session_state.messages.append({"role": "assistant", "content": response})