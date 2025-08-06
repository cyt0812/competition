import streamlit as st
import subprocess
import psutil
import os
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
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
    "selected_json": "",  # 选中的JSON文件
    "begin_execution": False
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
    .stop-btn {
        background-color: #ea4335 !important;
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
    .json-select-container {
        position: relative;
        width: 100%;
    }
    .custom-select {
        width: 100%;
        max-width: 100%;
        padding: 8px 12px;
        border: 1px solid #ddd;
        border-radius: 6px;
        background-color: white;
        font-size: 14px;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23333' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        cursor: pointer;
        height: 36px;
        box-sizing: border-box;
    }
    .custom-select:disabled {
        background-color: #f0f0f0;
        cursor: not-allowed;
        color: #999;
    }
    .custom-select:focus {
        outline: none;
        border-color: #1a73e8;
        box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
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

# 侧边栏
with st.sidebar:
    st.header("🕘 历史对话")

    # 初始化（必须放在最前面）
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
    if st.button("🧹 清空记录", disabled=st.session_state.get("executing")):
        st.session_state.messages = []
        st.rerun()

    # 添加ADB测试按钮到侧栏
    st.write(f"**运行前请先点击ADB测试按钮↓**")
    command_adb = "adb devices"
    if st.button("📱 ADB测试", disabled=st.session_state.get("executing")):
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

# 读取JSON文件列表（包含所有JSON文件，不排除联通相关）
json_dir = os.path.join("data", "Mobile-Eval-E")
json_files = []
try:
    for file in os.listdir(json_dir):
        if file.endswith(".json"):
            json_files.append(file)
    json_files.sort()
except FileNotFoundError:
    st.error(f"❌ 未找到目录: {json_dir}")

# JSON文件到简短标题的映射（下拉框显示用，包含所有任务）
json_to_short_title = {
    "China_Union_Rewards_tasks.json": "联通领取权益",
    "Taobao_tasks.json": "淘宝加购飞鸟集",
    "China_Union_check_bill_tasks.json": "联通查询详细账单",
    "Weather_Notes_tasks.json": "查询天气并记录到备忘录",
    "China_Union_bill_tasks.json": "联通查询话费及充值",
    "WeChat_tasks.json": "微信群聊点赞发朋友圈",
    "Meituan_tasks.json": "美团下单黄焖鸡",
    "Suishouji_tasks.json": "随手记APP记录就餐费",
    "China_Union_harassment_simple_task.json": "联通拦截骚扰电话"
}

# JSON文件到原始长标题的映射（执行任务时显示用，包含所有任务）
json_to_original_title = {
    "China_Union_Rewards_tasks.json": "在中国联通App福利中心领取一项权益",
    "Taobao_tasks.json": "在淘宝搜《飞鸟集》，按低价排序，选两个最便宜的加购并停在购物车",
    "China_Union_check_bill_tasks.json": "在中国联通App进入“我的账单”，查看费用详细子账单",
    "Weather_Notes_tasks.json": "用浏览器搜未来几天天气，记录到备忘录并保存",
    "China_Union_bill_tasks.json": "在中国联通App查剩余话费，低于60元用支付宝充值，否则停止",
    "WeChat_tasks.json": "打开微信，给群聊“ZhouLei”发消息、给随机朋友圈点赞、发含照片和20字以上描述的朋友圈",
    "Meituan_tasks.json": "在美团点不超20元且优先近距离的黄焖鸡米饭外卖",
    "Suishouji_tasks.json": "用随手记记录今日外出就餐花费80元",
    "China_Union_harassment_simple_task.json": "在中国联通App服务板块的安全管家设置骚扰电话拦截并保存"
}


# 处理下拉选择框变更的函数
def update_selected_json():
    selected_display = st.session_state.json_selector
    if display_names and selected_display in display_names:
        selected_idx = display_names.index(selected_display)
        st.session_state.selected_json = json_files[selected_idx]


# JSON文件选择器和执行按钮（调整为同一行不换行）
if json_files:
    # 调整列比例，确保选择框和按钮在同一行
    col_empty, col_select, col_exec = st.columns([4, 3, 1.5])
    with col_empty:
        pass  # 空列占位，将内容推到右侧
    with col_select:
        # 初始化默认选中项
        if not st.session_state.selected_json and json_files:
            st.session_state.selected_json = json_files[0]

        # 创建显示名称列表（使用简短标题）
        display_names = []
        for file in json_files:
            display_name = json_to_short_title.get(file, os.path.splitext(file)[0])
            display_names.append(display_name)

        # 确定当前选中项的索引
        try:
            selected_idx = json_files.index(st.session_state.selected_json)
        except ValueError:
            selected_idx = 0

        # 创建选择框，添加on_change回调确保状态更新
        selected_display = st.selectbox(
            "选择任务文件",
            display_names,
            index=selected_idx,
            disabled=st.session_state.executing,
            label_visibility="collapsed",
            key="json_selector",
            on_change=update_selected_json
        )
    with col_exec:
        json_exec_clicked = st.button(
            "执行选中任务",
            key="json_exec_btn",
            disabled=st.session_state.input_disabled or not json_files or st.session_state.executing,
            help="执行左侧下拉选择框的预置任务",
            use_container_width=True
        )
else:
    st.warning("⚠️ 未找到任务文件")
    json_exec_clicked = False

# 输入框以及语音输入，发送，停止三个按钮
# 调整列宽比例，给停止按钮更多空间
input_cols = st.columns([10, 1, 1.2], gap="small")
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
    if st.button("停止任务", disabled=not st.session_state.get("executing"), use_container_width=True):
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

# 按钮样式处理
st.markdown("""
<script>
    // 执行任务按钮样式
    document.querySelector('[data-testid="stButton"]:nth-of-type(5) button')
        ?.classList.add('main-btn');
    // 麦克风按钮样式
    document.querySelector('.mic-recorder-container button')
        ?.classList.add('main-btn', 'mic-btn');
    // 停止任务按钮样式 - 确保文字不换行并调整宽度
    const stopButton = document.querySelector('[data-testid="stButton"]:nth-of-type(6) button');
    if (stopButton) {
        stopButton.classList.add('main-btn', 'stop-btn');
        stopButton.style.whiteSpace = 'nowrap';  // 防止文字换行
        stopButton.style.minWidth = '80px';      // 适当增加按钮宽度
    }
    // 禁用按钮样式
    document.querySelectorAll('button:disabled')
        .forEach(btn => btn.classList.add('disabled-btn'));
</script>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 语音转文字
def speech_to_text(audio_data):
    r = sr.Recognizer()
    try:
        return r.recognize_google(audio_data, language="zh-CN")
    except sr.UnknownValueError:
        return "无法识别语音"
    except sr.RequestError as e:
        return f"语音服务请求失败: {e}"

# 处理语音输入
if audio and not st.session_state.input_disabled:
    st.session_state.voice_active = True
    with st.chat_message("user"):
        st.markdown("🎤 正在识别语音...")
    audio_data = sr.AudioData(audio["bytes"], sample_rate=audio["sample_rate"], sample_width=2)
    recognized_text = speech_to_text(audio_data)
    st.session_state.messages.append({"role": "user", "content": recognized_text})
    st.session_state.task_to_execute = recognized_text
    st.session_state.input_disabled = True
    st.session_state.executing = True
    st.session_state.voice_active = False
    st.rerun()

# 处理chat_input
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

# 处理选中JSON文件的执行
if json_exec_clicked and not st.session_state.input_disabled and json_files and not st.session_state.executing:
    selected_file = st.session_state.selected_json
    file_path = os.path.join(json_dir, selected_file)
    instructions = load_task_instructions(file_path)
    if instructions:
        # 使用原始长标题显示在聊天记录中
        original_name = json_to_original_title.get(selected_file, os.path.splitext(selected_file)[0])
        st.session_state.messages.append({"role": "user", "content": f"执行任务: {original_name}"})
        st.session_state.task_to_execute = "\n".join(instructions)
        st.session_state.input_disabled = True
        st.session_state.executing = True
        st.rerun()

# 聊天状态初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "executing" not in st.session_state:
    st.session_state.executing = False

if "pid" not in st.session_state:
    st.session_state.pid = None
if "begin_execution" not in st.session_state:
    st.session_state.begin_execution = False

# 执行任务逻辑
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