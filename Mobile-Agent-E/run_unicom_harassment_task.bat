@echo off
echo ========================================
echo 联通App骚扰电话拦截设置任务
echo ========================================
echo.
echo 请确保：
echo 1. 已设置环境变量 BACKBONE_TYPE=Qwen
echo 2. 已设置环境变量 QWEN_API_KEY=你的API密钥
echo 3. 手机已通过USB连接并开启ADB调试
echo 4. 手机已安装联通app
echo 5. 手机屏幕已解锁
echo.
pause
echo.
echo 开始执行任务...
echo.

python run.py --run_name unicom_harassment --setting individual --tasks_json data/unicom_harassment_block_task.json

echo.
echo ========================================
echo 任务执行完成！
echo 结果保存在: logs/qwen-max/mobile_agent_E/unicom_harassment/
echo ========================================
pause