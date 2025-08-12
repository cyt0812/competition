import dashscope
import os
import sys
import io

# ─── 防止 Windows 控制台 GBK 编码错误 ─────────────────────────────────────
# 将 stdout/stderr 强制设置为 UTF-8 编码，并在遇到无法编码的字符时替换
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
# ────────────────────────────────────────────────────────────────────────────

from inference_agent_E import run_single_task
from inference_agent_E import Perceptor, DEFAULT_PERCEPTION_ARGS, ADB_PATH, INIT_TIPS, INIT_SHORTCUTS, REASONING_MODEL
import torch
import sys as _sys  # 避免与上面 sys 冲突
from pathlib import Path
import json
import shutil
import time
import logging


# 获取截图目录（优先级：环境变量 > 默认值）
def get_screenshot_dir():
    env_dir = os.getenv('MOBILE_AGENT_SCREENSHOT_DIR')
    if env_dir:
        # 确保目录存在
        os.makedirs(env_dir, exist_ok=True)
        return env_dir

    # 默认路径 - 使用绝对路径
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshot')
    os.makedirs(default_dir, exist_ok=True)
    return default_dir


screenshot_path = os.path.join(get_screenshot_dir(), 'screenshot.png')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--log_root", type=str, default=None)
    parser.add_argument("--run_name", type=str, default="test")
    parser.add_argument("--instruction", type=str, default=None)
    parser.add_argument("--tasks_json", type=str, default=None)
    parser.add_argument("--specified_tips_path", type=str, default=None)
    parser.add_argument("--specified_shortcuts_path", type=str, default=None)
    parser.add_argument("--setting", type=str, default="individual", choices=["individual", "evolution"])
    parser.add_argument("--max_itr", type=int, default=40)
    parser.add_argument("--max_consecutive_failures", type=int, default=5)
    parser.add_argument("--max_repetitive_actions", type=int, default=5)
    parser.add_argument("--overwrite_task_log_dir", action="store_true", default=False)
    parser.add_argument("--enable_experience_retriever", action="store_true", default=False)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--screenrecord", action="store_true", default=False)

    args = parser.parse_args()
    torch.manual_seed(args.seed)

    if args.log_root is None:
        args.log_root = f"logs/{REASONING_MODEL}/mobile_agent_E"

    if args.instruction is None and args.tasks_json is None:
        raise ValueError("You must provide either instruction or tasks_json.")
    if args.instruction is not None and args.tasks_json is not None:
        raise ValueError("You cannot provide both instruction and tasks_json.")

    default_perceptor_args = DEFAULT_PERCEPTION_ARGS
    # run inference
    if args.instruction is not None:
        # single task inference
        try:
            run_single_task(
                args.instruction,
                run_name=args.run_name,
                log_root=args.log_root,
                tips_path=args.specified_tips_path,
                shortcuts_path=args.specified_shortcuts_path,
                persistent_tips_path=None,
                persistent_shortcuts_path=None,
                perceptor=None,
                perception_args=default_perceptor_args,
                max_itr=args.max_itr,
                max_consecutive_failures=args.max_consecutive_failures,
                max_repetitive_actions=args.max_repetitive_actions,
                overwrite_log_dir=args.overwrite_task_log_dir,
                enable_experience_retriever=args.enable_experience_retriever,
                temperature=args.temperature,
                screenrecord=args.screenrecord
            )
        except Exception as e:
            print(f"Failed when doing task: {args.instruction}")
            print("ERROR:", e)
    else:
        # multi task inference
        task_json = json.load(open(args.tasks_json, "r"))
        if "tasks" in task_json:
            tasks = task_json["tasks"]
        else:
            tasks = task_json

        perceptor = Perceptor(ADB_PATH, perception_args=default_perceptor_args)

        run_log_dir = f"{args.log_root}/{args.run_name}"
        os.makedirs(run_log_dir, exist_ok=True)

        if args.setting == "individual":
            ## individual setting ##
            persistent_tips_path = None
            persistent_shortcuts_path = None

        elif args.setting == "evolution":
            ## evolution setting: tasks share a persistent long-term memory with continue updating tips and shortcuts##
            persistent_tips_path = os.path.join(run_log_dir, "persistent_tips.txt")
            persistent_shortcuts_path = os.path.join(run_log_dir, "persistent_shortcuts.json")

            if args.specified_tips_path is not None:
                shutil.copy(args.specified_tips_path, persistent_tips_path)
            elif not os.path.exists(persistent_tips_path):
                with open(persistent_tips_path, "w", encoding="utf-8") as f:
                    f.write(INIT_TIPS)
            if args.specified_shortcuts_path is not None:
                shutil.copy(args.specified_shortcuts_path, persistent_shortcuts_path)
            elif not os.path.exists(persistent_shortcuts_path):
                with open(persistent_shortcuts_path, "w") as f:
                    json.dump(INIT_SHORTCUTS, f, indent=4)
        else:
            raise ValueError("Invalid setting:", args.setting)

        error_tasks = []
        print(f"INFO: Running tasks from {args.tasks_json} using {args.setting} setting ...")
        for i, task in enumerate(tasks):
            ## if future tasks are visible, specify them in the args ##
            future_tasks = [t['instruction'] for t in tasks[i + 1:]]

            print("\n\n### Running on task:", task["instruction"])
            print("\n\n")
            instruction = task["instruction"]
            if "task_id" in task:
                task_id = task["task_id"]
            else:
                task_id = args.tasks_json.split("/")[-1].split(".")[0] + f"_{args.setting}" + f"_{i}"
            try:
                run_single_task(
                    instruction,
                    future_tasks=future_tasks,
                    log_root=args.log_root,
                    run_name=args.run_name,
                    task_id=task_id,
                    tips_path=args.specified_tips_path,
                    shortcuts_path=args.specified_shortcuts_path,
                    persistent_tips_path=persistent_tips_path,
                    persistent_shortcuts_path=persistent_shortcuts_path,
                    perceptor=perceptor,
                    perception_args=default_perceptor_args,
                    max_itr=args.max_itr,
                    max_consecutive_failures=args.max_consecutive_failures,
                    max_repetitive_actions=args.max_repetitive_actions,
                    overwrite_log_dir=args.overwrite_task_log_dir,
                    enable_experience_retriever=args.enable_experience_retriever,
                    temperature=args.temperature,
                    screenrecord=args.screenrecord
                )
                print("\n\nDONE:", task["instruction"])
                print("IMPORTANT: Please reset the device as needed before running the next task!")
                input("Press Enter to continue to next task ...")
            except Exception as e:
                print(f"Failed when doing task: {instruction}")
                print("ERROR:", e)
                error_tasks.append(task_id)
        error_task_output_path = f"{run_log_dir}/error_tasks.json"
        with open(error_task_output_path, "w", encoding="utf-8") as f:
            json.dump(error_tasks, f, indent=4, ensure_ascii=False)


def load_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        raise


# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    main()
