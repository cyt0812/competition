@echo off
set TASK_JSON_PATH=data/Mobile-Eval-E/WeChat_tasks.json
set SETTING=evolution
python run.py --run_name "shopping-tasks-0-%SETTING%" --setting %SETTING% --tasks_json "%TASK_JSON_PATH%" --overwrite_task_log_dir
