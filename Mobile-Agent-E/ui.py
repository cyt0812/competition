import streamlit as st
import subprocess

st.set_page_config(page_title="Mobile Agent Chat", layout="centered")

# 设置 logo 和标题在同一行
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logo/logo6.png", width=80)
with col2:
    st.title("Mobile Agent Chat")

# 聊天状态初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "executing" not in st.session_state:
    st.session_state.executing = False

# 显示聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 只在未执行状态下显示输入框
if not st.session_state.executing:
    prompt = st.chat_input("请输入任务指令，例如：打开微信并发送一条消息")

    if prompt:
        # 标记为执行中
        st.session_state.executing = True

        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 执行任务并输出
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🎯 正在执行任务，请稍候...\n")

            try:
                process = subprocess.Popen(
                    ["python", "run.py", "--run_name", "ui-task", "--setting", "individual", "--instruction", prompt],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                output_lines = []
                for line in process.stdout:
                    output_lines.append(line)
                    message_placeholder.markdown("```\n" + "".join(output_lines) + "\n```")

                process.wait()

            except Exception as e:
                output_lines.append(f"\n执行失败：{str(e)}")
                message_placeholder.markdown("```\n" + "".join(output_lines) + "\n```")

            # 保存 assistant 最终消息
            st.session_state.messages.append({
                "role": "assistant",
                "content": "```\n" + "".join(output_lines) + "\n```"
            })

        # 任务完成：更新状态 + 页面刷新
        st.session_state.executing = False
        st.rerun()  # 关键！刷新页面以恢复输入框