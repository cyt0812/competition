import streamlit as st
import subprocess
import psutil
import os
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
import magic  # 用于检测MIME类型
import io
import json
import time
import re

st.set_page_config(page_title="Mobile Agent Chat", layout="wide")

# 初始化状态
for key, default_value in {
    "messages": [],
    "executing": False,
    "input_disabled": False,
    "task_to_execute": None,
    "pid": None,
    "text_active": False,
    "voice_active": False,
    "begin_execution": False,
    "audio": None,
    "audio_data": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# 自定义样式
st.markdown(
    """
    <style>
    html, body, #root, .appview-container {
        height: 100vh !important;
        margin: 0; padding: 0;
        background: #f9f9f9;
    }
    .appview-container main {
        display: flex;
        flex-direction: column;
        height: 100vh;
        padding: 10px 20px 70px 20px;
        box-sizing: border-box;
        overflow: hidden;
    }
    #chat-container {
        flex-grow: 1;
        overflow-y: auto;
        color: #333;
        font-size: 16px;
        line-height: 1.4;
        padding-right: 10px;
        word-break: break-word;
    }
    .chat-message-user {
        margin-bottom: 12px;
        color: #1a73e8;
        font-weight: 600;
    }
    .chat-message-assistant {
        margin-bottom: 12px;
        color: #444;
        font-weight: 500;
        white-space: pre-wrap;
        background: #eef1f5;
        padding: 8px 12px;
        border-radius: 6px;
    }
    #input-area {
        position: fixed !important;
        bottom: 0;
        left: 280px;
        width: calc(100% - 280px);
        background: white;
        box-shadow: 0 -1px 6px rgb(0 0 0 / 0.1);
        padding: 8px 20px 12px 20px;
        box-sizing: border-box;
        z-index: 1000;
        user-select: none;
    }
    #input-row {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    #input-row input[type="text"] {
        flex-grow: 1;
        height: 36px;
        font-size: 15px;
        padding: 0 10px;
        border: 1px solid #ccc;
        border-radius: 6px;
        outline-offset: 0;
    }
    .main-btn {
        height: 36px;
        min-width: 60px;
        border-radius: 6px;
        background-color: #1a73e8;
        color: white;
        border: none;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        user-select: none;
    }
    .main-btn:hover {
        background-color: #155ab6;
        transform: translateY(-1px);
    }
    .mic-btn {
        background-color: #34a853 !important;
    }
    .mic-btn:hover {
        background-color: #2c8c46 !important;
    }
    .disabled-btn {
        background-color: #ccc !important;
        cursor: not-allowed;
        color: #666 !important;
        transform: none !important;
    }
    .small-task-btn {
        height: 24px !important;
        padding: 0 5px !important;
        font-size: 10px !important;
        min-width: auto !important;
        border-radius: 4px !important;
        background-color: #f0f2f6 !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        transition: all 0.2s ease !important;
    }
    .small-task-btn:hover {
        background-color: #e6e9ed !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 标题和logo
col1, col2 = st.columns([1, 5])
with col1:
    if os.path.exists("logo/logo6.png"):
        st.image("logo/logo6.png", width=80)
with col2:
    st.title("Mobile Agent Chat")

# 聊天消息区（历史）
st.markdown('<div id="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-message-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message-assistant">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# === 新增：专门的输出容器（位于页面流中，**在输入区之前**）
# 所有流式执行输出都会渲染到 output_container，这样保证显示位置在输入区上方
output_container = st.container()

ADB_PATH = os.environ.get("ADB_PATH", default="adb")

def reset():
    st.session_state.executing = False
    st.session_state.begin_execution = False
    st.session_state.input_disabled = False
    st.session_state.task_to_execute = None
    st.session_state.text_active = False
    st.session_state.voice_active = False

# 侧边栏
with st.sidebar:
    st.header("🕘 历史对话")

    #✅ 初始化（必须放在最前面）
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 显示历史记录
    if st.session_state.messages:
        for msg in st.session_state.messages:
            role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
            # content = msg["content"].strip() if msg["role"] == "user" else re.sub(r"<.*?>", "", msg["content"].strip().split("\n")[-1]).strip()
            content = msg["content"].strip() if msg["role"] == "user" else msg["content"].strip().split("\n")[-1]
            st.markdown(f"**{role}:**\n\n{content[:100]}{'...' if len(content) > 100 else ''}", unsafe_allow_html=True)
    else:
        st.info("暂无对话记录")

    # 添加清空按钮
    if st.button("🧹 清空记录",disabled= st.session_state.get("executing") or st.session_state.get("input_disabled"),use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # 添加ADB测试按钮到侧栏
    st.write(f"**运行前请先点击ADB测试按钮↓**")
    command_adb = ADB_PATH + " devices"
    if st.button("📱 ADB测试",disabled= st.session_state.get("executing") or st.session_state.get("input_disabled"), use_container_width=True):
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
            else:
                st.error("❌ 没有检测到设备，请检查连接")
        except subprocess.CalledProcessError as e:
            st.error("❌ ADB 工具未安装或未添加到环境变量")
            st.code(e.output)

# 底部输入区（固定）
st.markdown('<div id="input-area">', unsafe_allow_html=True)

# CSS 样式：按钮不换行、宽度固定
st.markdown("""
    <style>
    div.stButton > button {
        white-space: nowrap !important; /* 不换行 */
        overflow: hidden;
        text-overflow: ellipsis;
        height: 28px;                   /* 固定高度 */
        padding: 0 4px;                  /* 左右内边距 */
    }
    </style>
""", unsafe_allow_html=True)

# 根据索引从json文件的多个task种选择指定的task执行，默认是全选
def load_task_instructions(file_path, select="All"):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                data = json.load(f)
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gb2312') as f:
                    data = json.load(f)
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
    except FileNotFoundError:
        st.error(f"❌ 未找到任务文件: {file_path}")
        return []
    if select=="All":   
        return_instructions_list = [sub_task.get("instruction", "") for sub_task in data.get("tasks", []) if sub_task.get("instruction")]
    else:
        try:
            index = int(select) - 1  # 转成索引（假设 select 从 1 开始）
            tasks = [sub_task.get("instruction", "") for sub_task in data.get("tasks", []) if sub_task.get("instruction")]
            if 0 <= index < len(tasks):
                return_instructions_list = [tasks[index]]
            else:
                return_instructions_list = []
        except ValueError:
            # select 不是数字
            return_instructions_list = []

    return return_instructions_list

# 通用按钮处理函数
def handle_button_click(button_key, file_path, select=None):
    """处理按钮点击逻辑"""
    if st.session_state.get(button_key, False) and not st.session_state.input_disabled:
        instructions = load_task_instructions(file_path, select=select)
        if instructions:
            st.session_state.messages.append({"role": "user", "content": "\n".join(instructions)})
            st.session_state.task_to_execute = "\n".join(instructions)
            st.session_state.input_disabled = True
            st.session_state.executing = True
            st.rerun()

# 按钮配置（label, key, tooltip, 文件路径, select参数）
buttons = [
    ("充值", "bill_clicked", "联通话费查询，余额低于20元时充值", "data/Mobile-Eval-E/China_Union_bill_tasks.json", "All"),
    ("权益", "reward_clicked", "联通权益领取", "data/Mobile-Eval-E/China_Union_Rewards_tasks.json", "All"),
    ("账单", "billinfo_clicked", "查询联通账号当月详细账单", "data/Mobile-Eval-E/China_Union_check_bill_tasks.json", "All"),
    ("拦截", "harassment_clicked", "联通账号设置拦截骚扰电话", "data/Mobile-Eval-E/China_Union_harassment_simple_task.json", "1"),
    ("记账", "suihsouji_clicked", "随手记记账", "data/Mobile-Eval-E/SuiShouJi_tasks.json", "All"),
    ("淘宝", "taobao_clicked", "淘宝加购飞鸟集", "data/Mobile-Eval-E/Taobao_tasks.json", "All"),
    ("美团", "meituan_clicked", "美团外卖点一份黄焖鸡米饭", "data/Mobile-Eval-E/Meituan_tasks.json", "All"),
    ("微信", "webchat_clicked", "微信发朋友圈", "data/Mobile-Eval-E/WeChat_tasks.json", "3"),
    ("天气", "weather_clicked", "查看天气记录到Note", "data/Mobile-Eval-E/Weather_Notes_tasks.json", "All"),
]

# 自动等分列
cols = st.columns(len(buttons))

# 循环绘制按钮
for col, (label, key, tip, path, select) in zip(cols, buttons):
    with col:
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        clicked = st.button(label, key=key, help=tip, 
                                          disabled=st.session_state.input_disabled,
                                          use_container_width=True)
        if clicked:
            handle_button_click(key, path, select)

#输入框以及语音输入，发送，停止三个按钮
input_cols = st.columns([10, 1, 1], gap="small")
with input_cols[0]:
    user_text = st.chat_input(
        placeholder="请输入任务指令，例如：打开微信并发送一条消息给联系人周XX",
        key="custom_input",
        disabled=st.session_state.input_disabled or st.session_state.voice_active
    )

with input_cols[1]:
    mic_disabled = st.session_state.input_disabled or st.session_state.text_active
    if not mic_disabled:
        st.session_state.audio = mic_recorder(
            start_prompt="🎤",
            stop_prompt="⏹️",
            just_once=True,
            use_container_width=True,
        )
    else:
        st.button("🎤", disabled=True, use_container_width=True)

def is_valid_line(line: str) -> bool:
    """判断输出行是否有效（非空、非undefined）"""
    return bool(
        line
        and isinstance(line, str)
        and line.strip()
        and line.strip().lower() != "undefined"
)

with input_cols[2]:
    if st.button("停止", disabled=not st.session_state.get("executing"), use_container_width=True):
        pid = st.session_state.get("pid")
        if not st.session_state.executing:
            pid = None
        if pid:
            try:
                p = psutil.Process(pid)
                p.terminate()  # 或 p.kill()

                # 立即在 session_state messages 写入终止信息，保证新 run 能显示
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
                    raw_content = st.session_state.messages[-1]["content"]
                    # 拆成行，去掉脏数据
                    cleaned_lines = [
                        line for line in raw_content.splitlines() if is_valid_line(line)
                    ]
                    # 重新组合 + 高亮终止提示（等宽字体 + Markdown 保留）
                    final_content = (
                        "\n".join(cleaned_lines) +
                        "<div style='font-family: monospace; white-space: pre-wrap;'>"
                        + "\n<span style='color: orange;'>⚠️ 任务已手动终止</span>"
                        + "</div>"
                    )
                    st.session_state.messages[-1]["content"] = final_content
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": (
                            "<div style='font-family: monospace; white-space: pre-wrap;'>"
                            "<span style='color: orange;'>⚠️ 任务已手动终止</span>"
                            "</div>"
                        )
                    })

                reset()
                st.success("任务已终止")
                st.rerun()  # 刷新 UI，恢复输入状态
            except Exception as e:
                st.error(f"终止失败：{e}")
        else:
            st.warning("没有可终止的任务")

st.markdown('</div>', unsafe_allow_html=True)

#语音输入后rerun以在识别期间禁用按钮
if st.session_state.audio:
    st.session_state.audio_data=st.session_state.audio
    st.session_state.audio = None
    st.session_state.input_disabled = True
    st.session_state.voice_active = True
    st.rerun()

#语音转文字
def speech_to_text(audio_data):
    try:
        mime_type = magic.from_buffer(audio_data['bytes'], mime=True)
        print("🔍 Detected MIME type:", mime_type)

        # 判断是否为原始 PCM 格式
        is_pcm = mime_type in ["audio/L16", "audio/basic", "audio/x-wav", "audio/raw"]

        if not is_pcm:
            print("🎼 非PCM格式，开始转换为16kHz PCM mono...")
            # 非 PCM，则先转换成识别友好格式
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data["bytes"]), format="webm")
            pcm_audio = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            raw_audio = pcm_audio.raw_data
            sample_rate = pcm_audio.frame_rate
            sample_width = pcm_audio.sample_width
        else:
            print("✅ 已是PCM格式，直接使用原始字节")
            raw_audio = audio_data["bytes"]
            sample_rate = audio_data["sample_rate"]
            sample_width = 2  # 一般是 16-bit PCM（2 字节），也可以从其他字段获取更精确

        # 构造 speech_recognition 可识别的 AudioData
        recognizer = sr.Recognizer()
        audio_data = sr.AudioData(raw_audio, sample_rate, sample_width)
        return recognizer.recognize_google(audio_data, language="zh-CN"), None

    except sr.UnknownValueError:
        return "", "无法识别语音"
    except sr.RequestError as e:
        return "", f"语音服务请求失败: {e}"
    except Exception as e:
        return "", f"语音识别处理错误: {e}"

# 处理语音输入
if st.session_state.audio_data and st.session_state.voice_active:
    st.session_state.input_disabled = True
    with st.chat_message("user"):
        st.markdown("🎤 正在识别语音...")

    recognized_text, recognized_text_error = speech_to_text(st.session_state.audio_data)
    if not recognized_text_error:
        st.session_state.messages.append({"role": "user", "content": recognized_text})
        st.session_state.task_to_execute = recognized_text
        st.session_state.executing = True
        st.session_state.voice_active = False
        st.session_state.audio_data=None
        st.rerun()
    else:
        st.error(recognized_text_error + " 5秒后自动重置")
        st.session_state.voice_active = False
        st.session_state.audio_data=None
        st.session_state.input_disabled = False
        time.sleep(5)
        st.rerun()

#处理chat_input
if user_text and not st.session_state.input_disabled:
    st.session_state.text_active = True
    st.session_state.messages.append({"role": "user", "content": user_text.strip()})
    st.session_state.task_to_execute = user_text.strip()
    st.session_state.input_disabled = True
    st.session_state.executing = True
    st.rerun()

# --------------------------
# 任务执行逻辑（输出渲染到 output_container，保证位于输入之上）
# --------------------------
if st.session_state.task_to_execute and st.session_state.executing and not st.session_state.begin_execution:
    st.session_state.begin_execution = True
    prompt = st.session_state.task_to_execute
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        st.error("❌ 任务指令为空或无效")
        reset()
        st.rerun()
    if not os.path.exists("run.py"):
        st.error("❌ run.py 文件不存在")
        reset()
        st.stop()

    # 关键：把流式输出渲染到 output_container，保证它出现在所有输入组件的上方
    with output_container:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🎯 正在执行任务，请稍候...\n")
            output_lines = []

            try:
                # 流式子进程：文本模式 + 行缓冲 + UTF-8
                process = subprocess.Popen(
                    ["python", "-u", "run.py", "--run_name", "ui-task", "--setting", "individual", "--instruction", prompt],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                st.session_state.pid = process.pid

                module_flags = {m: False for m in [
                    'Perceptor', 'Manager', 'Operator', 'Action Reflector',
                    'NoteKeeper', 'Experience Reflector'
                ]}

                if not st.session_state.messages or st.session_state.messages[-1]["role"] != "assistant":
                    st.session_state.messages.append({"role": "assistant", "content": "```\n(执行中...)\n```"})
                else:
                    st.session_state.messages[-1]["content"] = "```\n(执行中...)\n```"

                # 实时逐行读取
                for decoded_line in process.stdout:
                    display_line = True
                    formatted_line = decoded_line

                    # 检测当前模块
                    for module in module_flags:
                        if module.lower() in decoded_line.lower() and 'thinking' not in decoded_line.lower():
                            module_flags = {m: (m == module) for m in module_flags}
                            break

                    # 高亮关键步骤
                    module_keywords = {
                        'Manager': ['Current Subgoal:'],
                        'Operator': ['Executing atomic action:'],
                        'Action Reflector': ['Progress Status:'],
                        'Experience Reflector': ['Progress Logs:', 'Finish Thought:']
                    }
                    for module, keywords in module_keywords.items():
                        if module_flags[module]:
                            for keyword in keywords:
                                if keyword.lower() in decoded_line.lower():
                                    escaped_line = decoded_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                    formatted_line = f'<span style="color: blue;">{escaped_line}</span>'
                                    break
                            break

                    if is_valid_line(formatted_line):
                        output_lines.append(formatted_line)

                    # 更新 session_state
                    cleaned_output = [line for line in output_lines if is_valid_line(line)]
                    #st.session_state.messages[-1]["content"] = "```\n" + "".join(cleaned_output) + "\n```"
                    st.session_state.messages[-1]["content"] = "".join(cleaned_output)

                    # 实时刷新 UI
                    message_placeholder.markdown(
                        "\n".join(cleaned_output),
                        unsafe_allow_html=True
                    )

                process.wait()

                # 根据返回状态标记任务结果
                result_color = 'green'
                if (process.returncode != 0 or
                    any('执行失败' in line for line in output_lines) or
                    any('ERROR:' in line and line.split('ERROR:', 1)[1].strip() for line in output_lines) or
                    (any('error' in line.lower() for line in output_lines) and
                    not any('Error Description: None' in line for line in output_lines))):
                    result_color = 'red'

                result_line = f'<span style="color: {result_color};">任务{"成功完成" if result_color == "green" else "执行失败"}</span>'
                output_lines.append(result_line)

                cleaned_output = [line for line in output_lines if is_valid_line(line)]
                #st.session_state.messages[-1]["content"] = "```\n" + "".join(cleaned_output) + "\n```"
                st.session_state.messages[-1]["content"] = "".join(cleaned_output)
                message_placeholder.markdown(
                    "\n".join(cleaned_output),
                    unsafe_allow_html=True
                )

            except Exception as e:
                error_line = f"<span style='color: red;'>执行失败：{str(e)}</span>"
                output_lines.append(error_line)
                cleaned_output = [line for line in output_lines if is_valid_line(line)]
                #st.session_state.messages[-1]["content"] = "```\n" + "".join(cleaned_output) + "\n```"
                st.session_state.messages[-1]["content"] = "".join(cleaned_output)
                message_placeholder.markdown(
                    "\n".join(cleaned_output),
                    unsafe_allow_html=True
                )

    reset()
    st.success("✅ 任务完成，输入已恢复")
    st.rerun()
