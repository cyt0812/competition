@echo off

:: 设置环境变量
set ADB_PATH=D:\adb\platform-tools\adb
set BACKBONE_TYPE=Qwen
set QWEN_API_KEY=sk-b8cb5b51cfb54dd483cb5329c7ea0b42

:: 运行Python脚本
python Mobile-Agent-E/run.py --tasks_json data/unicom_security_guard_stats.json --run_name unicom_test --setting evolution --overwrite_task_log_dir

:: 保持窗口打开以便查看输出
pause