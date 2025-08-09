
TASK_JSON_PATH="data/Mobile-Eval-E/WeChat_tasks.json"
SETTING="evolution"
python run.py \
    --run_name "example-$SETTING" \
    --setting $SETTING \
    --tasks_json "$TASK_JSON_PATH" 
