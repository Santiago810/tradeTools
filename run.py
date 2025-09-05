#!/usr/bin/env python
"""
启动脚本 - A股两融交易查询系统
简化安装和启动流程
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"当前版本: Python {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import pandas
        import numpy
        import matplotlib
        import seaborn
        import requests
        import streamlit
        print("✅ 主要依赖包检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        return False

def install_dependencies():
    """安装依赖"""
    print("🔧 正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖包安装失败")
        return False

def create_directories():
    """创建必要的目录"""
    directories = ["data", "output", "logs", "temp"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ 目录结构创建完成")

def show_menu():
    """显示主菜单"""
    print("\n" + "="*50)
    print("🚀 A股两融交易查询系统")
    print("="*50)
    print("请选择启动方式:")
    print("1. 🌐 Web界面 (推荐)")
    print("2. 💻 命令行界面")
    print("3. 🔧 安装/更新依赖")
    print("4. 📖 查看帮助")
    print("5. 🚪 退出")
    print("="*50)

def launch_web_app():
    """启动Web应用"""
    print("🌐 正在启动Web界面...")
    print("请稍等，浏览器将自动打开...")
    print("如果浏览器未自动打开，请手动访问: http://localhost:8501")
    print("按 Ctrl+C 可以停止服务")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Web服务已停止")
    except Exception as e:
        print(f"❌ 启动Web界面失败: {e}")

def launch_cli_app():
    """启动命令行应用"""
    print("💻 正在启动命令行界面...")
    try:
        subprocess.run([sys.executable, "main.py", "--interactive"])
    except Exception as e:
        print(f"❌ 启动命令行界面失败: {e}")

def show_help():
    """显示帮助信息"""
    print("\n📖 使用帮助")
    print("-" * 30)
    print("1. Web界面:")
    print("   - 功能最完整，推荐新用户使用")
    print("   - 提供可视化图表和交互式操作")
    print("   - 在浏览器中运行")
    
    print("\n2. 命令行界面:")
    print("   - 适合高级用户和自动化场景")
    print("   - 支持批量处理和脚本调用")
    print("   - 更快的数据处理速度")
    
    print("\n3. 系统要求:")
    print("   - Python 3.8+")
    print("   - 网络连接")
    print("   - 约100MB磁盘空间")
    
    print("\n4. 数据源:")
    print("   - AKShare: 免费开源数据接口")
    print("   - TuShare: 专业金融数据（需要Token）")
    print("   - 东方财富: 实时行情数据")
    
    print("\n5. 常见问题:")
    print("   - 首次运行需要安装依赖包")
    print("   - 数据获取可能需要几十秒时间")
    print("   - 建议查询时间范围不超过1年")
    
    input("\n按回车键返回主菜单...")

def main():
    """主函数"""
    # 切换到脚本所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🔍 正在检查系统环境...")
    
    # 检查Python版本
    if not check_python_version():
        input("按回车键退出...")
        return
    
    # 创建目录
    create_directories()
    
    # 检查依赖
    deps_ok = check_dependencies()
    
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择 (1-5): ").strip()
            
            if choice == '1':
                if not deps_ok:
                    print("❌ 依赖包未安装，请先选择选项3安装依赖")
                    continue
                launch_web_app()
                
            elif choice == '2':
                if not deps_ok:
                    print("❌ 依赖包未安装，请先选择选项3安装依赖")
                    continue
                launch_cli_app()
                
            elif choice == '3':
                if install_dependencies():
                    deps_ok = check_dependencies()
                    
            elif choice == '4':
                show_help()
                
            elif choice == '5':
                print("👋 感谢使用，再见！")
                break
                
            else:
                print("❌ 无效选择，请输入1-5")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序已退出")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()