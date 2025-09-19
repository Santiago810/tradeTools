#!/usr/bin/env python
"""
启动Web界面脚本
"""

import subprocess
import sys
import socket

def find_free_port(start_port=8501):
    """查找可用端口"""
    port = start_port
    while port < start_port + 10:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    return None

def start_web():
    """启动Web界面"""
    print("🚀 启动A股金融数据分析系统...")
    
    # 查找可用端口
    port = find_free_port()
    if not port:
        print("❌ 无法找到可用端口 (8501-8510)")
        return
    
    print(f"🌐 Web界面将在 http://localhost:{port} 启动")
    print("⏹️  按 Ctrl+C 停止服务\n")
    
    try:
        # 启动streamlit应用
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py", 
            "--server.port", str(port),
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n👋 Web服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    start_web()