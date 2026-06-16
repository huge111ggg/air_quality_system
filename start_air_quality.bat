@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo 正在启动城市空气质量等级预测系统...
echo.
echo 第1步：生成数据集
python generate_dataset.py
if errorlevel 1 goto error
echo.
echo 第2步：训练模型
python train_model.py
if errorlevel 1 goto error
echo.
echo 第3步：启动网页服务
echo 浏览器打开：http://127.0.0.1:5001
echo 注意：请不要关闭这个窗口，关闭后网页也会停止。
python app.py
goto end

:error
echo.
echo 运行失败。请截图这个窗口里的错误信息发给我。
pause

:end
