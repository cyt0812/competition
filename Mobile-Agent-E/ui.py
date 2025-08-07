import streamlit as st
import subprocess
import psutil
import os
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
import io
import json
import time

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
    st.image("logo/logo6.png", width=80)
with col2:
    st.title("Mobile Agent Chat")

# 聊天消息区
st.markdown('<div id="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-message-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message-assistant">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

ADB_PATH = os.environ.get("ADB_PATH", default="adb")

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
            content = msg["content"].strip()
            st.markdown(f"**{role}:**\n\n{content[:100]}{'...' if len(content) > 100 else ''}")
    else:
        st.info("暂无对话记录")

    # 添加清空按钮
    if st.button("🧹 清空记录",disabled= st.session_state.get("executing"),use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # 添加ADB测试按钮到侧栏
    st.write(f"**运行前请先点击ADB测试按钮↓**")
    command_adb = ADB_PATH + " devices"
    if st.button("📱 ADB测试",disabled= st.session_state.get("executing"), use_container_width=True):
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

# 底部输入区
st.markdown('<div id="input-area">', unsafe_allow_html=True)
mode_task_cols = st.columns([4, 1, 1])
with mode_task_cols[0]:
    st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
with mode_task_cols[1]:
    bill_clicked = st.button(
        "联通话费充值",
        key="bill_btn",
        disabled=st.session_state.input_disabled,
        help="余额低于20元时充值",
        use_container_width=True
    )

with mode_task_cols[2]:
    reward_clicked = st.button(
        "权益领取",
        key="reward_btn",
        disabled=st.session_state.input_disabled,
        help="联通权益领取",
        use_container_width=True
    )

#输入框以及语音输入，发送，停止三个按钮
input_cols = st.columns([10, 1, 1], gap="small")
with input_cols[0]:
    user_text = st.chat_input(
        placeholder="请输入任务指令，例如：打开微信并发送一条消息",
        key="custom_input",
        disabled=st.session_state.input_disabled or st.session_state.voice_active
    )

with input_cols[1]:
    mic_disabled = st.session_state.input_disabled or st.session_state.text_active
    audio = None
    if not mic_disabled:
        audio = mic_recorder(
            start_prompt="🎤",
            stop_prompt="⏹️",
            just_once=True,
            use_container_width=True,
        )
    else:
        st.button("🎤", disabled=True, use_container_width=True)

with input_cols[2]:
    if st.button("停止", disabled=not st.session_state.get("executing"), use_container_width=True):
        pid = st.session_state.get("pid")
        if not st.session_state.executing:
            pid = None
        if pid:
            try:
                p = psutil.Process(pid)
                p.terminate()  # 或 p.kill()
                st.session_state.executing = False
                st.session_state.begin_execution = False
                st.session_state.input_disabled = False
                st.session_state.task_to_execute = None
                st.session_state.text_active = False
                st.session_state.voice_active = False
                st.success("任务已终止")
                st.rerun()  # 刷新 UI，恢复输入状态
            except Exception as e:
                st.error(f"终止失败：{e}")
        else:
            st.warning("没有可终止的任务")

st.markdown('</div>', unsafe_allow_html=True)

# 使用 pydub + speech_recognition 实现 webm 语音识别
def speech_to_text(audio):
    try:
        print("🎧 audio keys:", audio.keys())
        print("📏 sample_rate:", audio["sample_rate"])
        print("📦 audio bytes type:", type(audio["bytes"]), "len:", len(audio["bytes"]))

        import magic  # 用于检测MIME类型
        mime_type = magic.from_buffer(audio['bytes'], mime=True)
        print("🔍 Detected MIME type:", mime_type)

        # 判断是否为原始 PCM 格式
        is_pcm = mime_type in ["audio/L16", "audio/basic", "audio/x-wav", "audio/raw"]

        if not is_pcm:
            print("🎼 非PCM格式，开始转换为16kHz PCM mono...")
            # 非 PCM，则先转换成识别友好格式
            audio_segment = AudioSegment.from_file(io.BytesIO(audio["bytes"]), format="webm")
            pcm_audio = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            raw_audio = pcm_audio.raw_data
            sample_rate = pcm_audio.frame_rate
            sample_width = pcm_audio.sample_width
        else:
            print("✅ 已是PCM格式，直接使用原始字节")
            raw_audio = audio["bytes"]
            sample_rate = audio["sample_rate"]
            sample_width = 2  # 一般是 16-bit PCM（2 字节），也可以从其他字段获取更精确

        # 构造 speech_recognition 可识别的 AudioData
        recognizer = sr.Recognizer()
        audio_data = sr.AudioData(raw_audio, sample_rate, sample_width)
        return recognizer.recognize_google(audio_data, language="zh-CN")

    except sr.UnknownValueError:
        return "无法识别语音"
    except sr.RequestError as e:
        return f"语音服务请求失败: {e}"
    except Exception as e:
        return f"语音识别处理错误: {e}"

if audio and not st.session_state.input_disabled:
    st.session_state.input_disabled = True
    st.session_state.voice_active = True
    with st.chat_message("user"):
        st.markdown("🎤 正在识别语音...")

    recognized_text, recognized_text_error = speech_to_text(audio)
    if not recognized_text_error:
        st.session_state.messages.append({"role": "user", "content": recognized_text})
        st.session_state.task_to_execute = recognized_text
        st.session_state.executing = True
        st.session_state.voice_active = False
        st.rerun()
    else:
        st.error(recognized_text_error + " 3秒后自动重置")
        st.session_state.voice_active = False
        st.session_state.input_disabled = False
        time.sleep(3)
        st.rerun()

#处理chat_input
if user_text and not st.session_state.input_disabled:
    st.session_state.text_active = True
    st.session_state.messages.append({"role": "user", "content": user_text.strip()})
    st.session_state.task_to_execute = user_text.strip()
    st.session_state.input_disabled = True
    st.session_state.executing = True
    st.rerun()

# 尝试多种编码方式读取文件
def load_task_instructions(file_path):
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
    return [sub_task.get("instruction", "") for sub_task in data.get("tasks", []) if sub_task.get("instruction")]

# 聊天状态初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "executing" not in st.session_state:
    st.session_state.executing = False

# 处理话费充值按钮点击
if bill_clicked and not st.session_state.input_disabled:
    instructions = load_task_instructions("data/Mobile-Eval-E/China_Union_bill_tasks.json")
    if instructions:
        st.session_state.messages.append({"role": "user", "content": "话费充值"})
        st.session_state.task_to_execute = "\n".join(instructions)
        st.session_state.input_disabled = True
        st.session_state.executing = True
        st.rerun()

# 处理权益领取按钮点击
if reward_clicked and not st.session_state.input_disabled:
    instructions = load_task_instructions("data/Mobile-Eval-E/China_Union_Rewards_tasks.json")
    if instructions:
        st.session_state.messages.append({"role": "user", "content": "权益领取"})
        st.session_state.task_to_execute = "\n".join(instructions)
        st.session_state.input_disabled = True
        st.session_state.executing = True
        st.rerun()

if "pid" not in st.session_state:
    st.session_state.pid = None
if "begin_execution" not in st.session_state:
    st.session_state.begin_execution = False



if "begin_execution" not in st.session_state:
    st.session_state.begin_execution = True
if "pid" not in st.session_state:
    st.session_state.pid = None

# 执行任务逻辑（核心修改：处理编码问题）
if st.session_state.task_to_execute and st.session_state.executing and not st.session_state.begin_execution:
    st.session_state.begin_execution = True
    prompt = st.session_state.task_to_execute
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        st.error("❌ 任务指令为空或无效")
        st.session_state.executing = False
        st.session_state.input_disabled = False
        st.session_state.task_to_execute = None
        st.session_state.text_active = False
        st.session_state.voice_active = False
        st.session_state.begin_execution = False
        st.rerun()
    if not os.path.exists("run.py"):
        st.error("❌ run.py 文件不存在")
        st.session_state.executing = False
        st.session_state.input_disabled = False
        st.session_state.task_to_execute = None
        st.session_state.text_active = False
        st.session_state.voice_active = False
        st.session_state.begin_execution = False
        st.stop()

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🎯 正在执行任务，请稍候...\n")
        output_lines = []
        try:
            # 关键修改：以二进制模式读取，不指定encoding
            process = subprocess.Popen(
                ["python", "run.py", "--run_name", "ui-task", "--setting", "individual", "--instruction", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            st.session_state.pid = process.pid

            # 读取二进制输出并尝试多编码解码
            for line in process.stdout:
                try:
                    # 优先UTF-8解码
                    decoded_line = line.decode('utf-8')
                except UnicodeDecodeError:
                    # 失败则尝试GBK
                    decoded_line = line.decode('gbk', errors='replace')
                output_lines.append(decoded_line)
                message_placeholder.markdown("```\n" + "".join(output_lines) + "\n```")
            process.wait()
        except Exception as e:
            output_lines.append(f"\n执行失败：{str(e)}")
            message_placeholder.markdown("```\n" + "".join(output_lines) + "\n```")

        st.session_state.messages.append(
            {"role": "assistant", "content": "```\n" + "".join(output_lines) + "\n```"}
        )
    st.session_state.executing = False
    st.session_state.input_disabled = False
    st.session_state.task_to_execute = None
    st.session_state.text_active = False
    st.session_state.voice_active = False
    st.session_state.begin_execution = False
    st.success("✅ 任务完成，输入已恢复")
    st.rerun()
