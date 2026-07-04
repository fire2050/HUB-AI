#!/usr/bin/env python3
"""
创建报价需求表三（钉钉AI多维表格）
使用方法：
1. 编辑 .env 文件，填写 DINGTALK_APP_KEY 和 DINGTALK_APP_SECRET
2. 运行: python create_table.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).parent / ".env")

from dingtalk_api import DingTalkAIClient


def main():
    print("=" * 60)
    print("🚀 创建报价需求表三（钉钉AI多维表格）")
    print("=" * 60)
    
    # 检查凭证
    app_key = os.environ.get("DINGTALK_APP_KEY", "")
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
    
    if not app_key or not app_secret:
        print("\n❌ 缺少钉钉应用凭证！")
        print("\n请编辑 dingtalk-openclaw-bridge/.env 文件，填写：")
        print("  DINGTALK_APP_KEY = 你的AppKey")
        print("  DINGTALK_APP_SECRET = 你的AppSecret")
        print("\n获取方式：")
        print("  1. 打开 https://open-dev.dingtalk.com/")
        print("  2. 进入 应用开发 → 企业内部开发 → 选择你的应用")
        print("  3. 在 应用信息 页面找到 AppKey 和 AppSecret")
        sys.exit(1)
    
    print(f"✅ 凭证已加载: {app_key[:6]}...{app_key[-4:]}")
    
    try:
        # 创建客户端
        client = DingTalkAIClient()
        
        # 测试token
        token = client.get_access_token()
        print(f"✅ Token获取成功: {token[:20]}...")
        
        # 创建表格
        print("\n📊 正在创建表格...")
        result = client.create_default_quote_table()
        
        print("\n" + "=" * 60)
        print("🎉 表格创建成功！")
        print("=" * 60)
        print(f"\n📋 表格ID: {result['table_id']}")
        print(f"   字段数量: {result['fields_count']}")
        print("\n📱 现在你可以：")
        print("  1. 在钉钉端查看和测试表格")
        print("  2. 配置自动化webhook回调")
        print("  3. 在群中 @AI+比特虾 说「报价」开始对话收集")
        
    except Exception as e:
        print(f"\n❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
