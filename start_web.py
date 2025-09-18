#!/usr/bin/env python
"""
启动Web界面测试脚本
"""

import subprocess
import sys
import os

def start_web():
    """启动Web界面"""
    print("🚀 启动板块资金查询Web界面...")
    print("📝 请在浏览器中测试以下功能:")
    print("   1. 点击'进入板块资金查询'")
    print("   2. 选择'板块概览'模式")
    print("   3. 点击'查询所有板块'")
    print("   4. 查看板块排行榜和图表")
    print("\n🌐 Web界面将在 http://localhost:8501 启动")
    print("⏹️  按 Ctrl+C 停止服务\n")
    
    try:
        # 启动streamlit应用
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"])
    except KeyboardInterrupt:
        print("\n👋 Web服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    start_web()