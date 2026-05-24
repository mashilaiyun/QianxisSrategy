@echo off
chcp 65001 >nul
echo ============================================================
echo    华为 OD 刷题知识库 - Web 服务器
echo ============================================================
echo.
echo 首次使用请先运行 build_kb.py 构建知识库
echo 构建后浏览器访问 http://localhost:8899
echo 按 Ctrl+C 停止服务器
echo.
python "%~dp0web_kb.py"
pause
