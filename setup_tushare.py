#!/usr/bin/env python
"""
TuShare配置助手
"""

import os
import sys

def setup_tushare():
    """配置TuShare"""
    print("🔧 TuShare配置助手")
    print("=" * 50)
    
    print("\n📖 TuShare简介:")
    print("TuShare是一个免费、开源的Python财经数据接口包")
    print("相比AKShare，TuShare更加稳定，但需要注册获取Token")
    
    print(f"\n📝 获取TuShare Token步骤:")
    print("1. 访问 https://tushare.pro/register")
    print("2. 注册账号并登录")
    print("3. 在用户中心获取Token")
    print("4. 将Token配置到系统中")
    
    # 检查当前配置
    from config import TUSHARE_TOKEN
    
    if TUSHARE_TOKEN:
        print(f"\n✅ 当前已配置TuShare Token: {TUSHARE_TOKEN[:10]}...")
        
        # 测试Token是否有效
        try:
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            pro = ts.pro_api()
            test_data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            
            if not test_data.empty:
                print(f"✅ Token有效，可以正常使用TuShare服务")
                return True
            else:
                print(f"⚠️ Token可能无效或权限不足")
                
        except Exception as e:
            print(f"❌ Token测试失败: {e}")
    else:
        print(f"\n❌ 未配置TuShare Token")
    
    # 配置Token
    print(f"\n🔧 配置TuShare Token:")
    print("请选择配置方式:")
    print("1. 设置环境变量（推荐）")
    print("2. 直接修改config.py文件")
    
    choice = input("\n请选择 (1-2): ").strip()
    
    if choice == '1':
        print(f"\n📋 环境变量配置方法:")
        print("在终端中执行以下命令:")
        print("")
        
        if os.name == 'nt':  # Windows
            print("Windows (CMD):")
            print("set TUSHARE_TOKEN=your_token_here")
            print("")
            print("Windows (PowerShell):")
            print("$env:TUSHARE_TOKEN='your_token_here'")
        else:  # macOS/Linux
            print("macOS/Linux:")
            print("export TUSHARE_TOKEN=your_token_here")
            print("")
            print("永久配置（添加到 ~/.bashrc 或 ~/.zshrc）:")
            print("echo 'export TUSHARE_TOKEN=your_token_here' >> ~/.bashrc")
        
        print(f"\n💡 配置完成后重新启动程序即可生效")
        
    elif choice == '2':
        token = input("\n请输入您的TuShare Token: ").strip()
        
        if token:
            try:
                # 读取config.py文件
                with open('config.py', 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 替换Token
                new_content = content.replace(
                    "TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')",
                    f"TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '{token}')"
                )
                
                # 写回文件
                with open('config.py', 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"✅ Token已保存到config.py文件")
                print(f"💡 重新启动程序后生效")
                
                return True
                
            except Exception as e:
                print(f"❌ 保存Token失败: {e}")
        else:
            print("❌ Token不能为空")
    
    else:
        print("❌ 无效选择")
    
    return False

def test_tushare_connection():
    """测试TuShare连接"""
    print(f"\n🧪 测试TuShare连接...")
    
    try:
        from config import TUSHARE_TOKEN
        
        if not TUSHARE_TOKEN:
            print("❌ 未配置TuShare Token")
            return False
        
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        # 测试基础接口
        print("测试股票基本信息接口...")
        stock_basic = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
        
        if not stock_basic.empty:
            print(f"✅ 股票基本信息: {len(stock_basic)} 条")
        
        # 测试概念板块接口
        print("测试概念板块接口...")
        concept_list = pro.concept()
        
        if not concept_list.empty:
            print(f"✅ 概念板块: {len(concept_list)} 个")
        
        # 测试日线数据接口
        print("测试日线数据接口...")
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        daily_basic = pro.daily_basic(trade_date=today)
        
        if not daily_basic.empty:
            print(f"✅ 日线数据: {len(daily_basic)} 条")
        
        print(f"\n🎉 TuShare连接测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ TuShare连接测试失败: {e}")
        
        if "权限" in str(e) or "permission" in str(e).lower():
            print("💡 可能是Token权限不足，请检查账号等级")
        elif "token" in str(e).lower():
            print("💡 可能是Token无效，请检查Token是否正确")
        else:
            print("💡 可能是网络问题或API限制")
        
        return False

if __name__ == "__main__":
    print("TuShare配置助手")
    
    if setup_tushare():
        test_tushare_connection()
    
    print(f"\n📖 更多信息:")
    print("- TuShare官网: https://tushare.pro")
    print("- 文档地址: https://tushare.pro/document/2")
    print("- 积分规则: https://tushare.pro/document/1?doc_id=13")