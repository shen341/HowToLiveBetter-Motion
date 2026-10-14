@echo off
title ComfyUI Server - NVIDIA GeForce RTX 4070
echo ==============================================================================
echo [HowToLiveBetter-Motion] 启动本地 ComfyUI 艺术原画服务 (RTX 4070)
echo 服务监听地址: http://127.0.0.1:8188
echo 虚拟环境路径: C:\stabilityMatrix\Packages\ComfyUI\venv
echo ==============================================================================
cd /d "C:\stabilityMatrix\Packages\ComfyUI"
"C:\stabilityMatrix\Packages\ComfyUI\venv\Scripts\python.exe" main.py --listen 127.0.0.1 --port 8188
pause
