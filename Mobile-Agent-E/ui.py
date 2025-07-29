import streamlit as st
import subprocess
import psutil
import os
import signal
import time

st.set_page_config(page_title="Mobile Agent Chat", layout="centered")

# 设置 logo 和标题在同一行
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logo/logo6.png", width=80)
with col2:
    st.title("Mobile Agent Chat")

#设置侧边栏，包含历史记录和删除按钮
with st.sidebar:
    st.header("🕘 历史对话")

    #✅ 初始化（必须放在最前面）
    if "messages" not in st.session_state:
        st.session_state.messages = []


    # 显示历史记录
    if st.session_state.messages:
        for msg in st.session_state.messages:
            role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
            content = msg["content"].strip()
            st.markdown(f"**{role}:**\n\n{content[:100]}{'...' if len(content) > 100 else ''}")
    else:
        st.info("暂无对话记录")

    # 添加清空按钮
    if st.button("🧹 清空记录"):
        st.session_state.messages = []
        st.rerun()

    # 添加ADB测试按钮到侧栏
    st.write(f"**运行前请先点击ADB测试按钮↓**")
    command_adb = "adb devices"
    if st.button("📱 ADB测试"):
        try:
            result = subprocess.check_output(command_adb, shell=True, text=True)
            device_num = result.count("device") - 1
            if device_num:
                device_serial_number = []
                lines = result.strip().split("\n")
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts = line.split()
                    device_serial_number.append(parts[0])
                device_serial_number = "\n".join(device_serial_number)
                st.success("✅ 已连接至" + str(device_num) + "个设备\n设备序列号：\n" + device_serial_number)
                # st.markdown(f"**设备序列号：**")
                # st.markdown(f"**{device_serial_number}**")
            else:
                st.error("❌ 请检查设备连接并确保已在设备上开启ADB调试功能")
        except subprocess.CalledProcessError as e:
            st.error("❌ 请正确安装ADB工具并将其添加到环境变量")
            st.code(e.output)

    #添加重置按钮到侧栏
    if "executing" not in st.session_state:
        st.session_state.executing = False
    st.write("**按下stop按钮后请点击重置任务状态按钮↓**")
    if st.button("🔄 重置任务状态"):
        st.session_state.executing = False
        st.rerun()

#添加退出按钮，按下后退出程序
# if st.button("退出程序"):
#     pid = os.getpid()
#     os.kill(pid, signal.SIGINT)

#添加终止按钮，按下后终止当前操作

# 聊天状态初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "executing" not in st.session_state:
    st.session_state.executing = False

# 显示聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def is_process_alive(pid):
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except Exception:
        return False

if "pid" not in st.session_state:
    st.session_state.pid = None

# if st.session_state.get("executing", False):
#     pid = st.session_state.get("pid")
#     if pid and not is_process_alive(pid):
#         st.warning("检测到任务已中断，自动重置状态")
#         st.session_state.executing = False
#         st.rerun()

if st.session_state.executing:
    pid = st.session_state.pid
    if pid and not is_process_alive(pid):
        st.warning("⚠️ 检测到任务已中断，状态已自动恢复")
        st.session_state.executing = False
        st.session_state.pid = None
        st.rerun()  # rerun 一次以更新 UI
        st.stop()   # 防止执行当前轮逻辑（这非常关键！）

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

                st.session_state.pid = process.pid
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