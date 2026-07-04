"""
钉钉多维表格API客户端
用于创建报价需求表三
"""
import os
import json
import time
import requests
from typing import Dict, List, Optional, Any

DINGTALK_API = "https://api.dingtalk.com/v1.0"


class DingTalkAIClient:
    """钉钉AI开放平台客户端"""
    
    def __init__(self, app_key: str = None, app_secret: str = None):
        self.app_key = app_key or os.environ.get("DINGTALK_APP_KEY", "")
        self.app_secret = app_secret or os.environ.get("DINGTALK_APP_SECRET", "")
        self._access_token = None
        self._token_expires_at = 0
        
        if not self.app_key or not self.app_secret:
            raise ValueError("请设置 DINGTALK_APP_KEY 和 DINGTALK_APP_SECRET")
    
    def get_access_token(self) -> str:
        """获取访问token"""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        
        url = "https://oapi.dingtalk.com/gettoken"
        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("errcode") != 0:
            raise Exception(f"获取token失败: {data.get('errmsg')}")
        
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]
        return self._access_token
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "x-acs-dingtalk-access-token": self.get_access_token(),
            "Content-Type": "application/json"
        }
    
    def create_ai_table(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        创建AI多维表格
        
        Args:
            name: 表格名称
            description: 表格描述
            
        Returns:
            table_id, view_id 等信息
        """
        url = f"{DINGTALK_API}/aiTables/tables"
        payload = {
            "name": name,
            "description": description
        }
        response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
        return response.json()
    
    def add_field(self, table_id: str, field_name: str, field_type: str, 
                  options: List[str] = None, required: bool = False) -> Dict[str, Any]:
        """
        添加字段
        
        Args:
            table_id: 表格ID
            field_name: 字段名称
            field_type: 字段类型: TEXT, TEXTAREA, NUMBER, SELECT, DATETIME, etc.
            options: 选项列表（SELECT类型时需要）
            required: 是否必填
        """
        url = f"{DINGTALK_API}/aiTables/{table_id}/fields"
        payload = {
            "fieldName": field_name,
            "fieldType": field_type,
            "required": required
        }
        if options:
            payload["options"] = [{"name": opt} for opt in options]
        
        response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
        return response.json()
    
    def create_default_quote_table(self) -> Dict[str, Any]:
        """
        创建默认的报价需求表三
        
        包含16个字段：
        - 7个必填字段（客户全称/联系人/联系电话/使用场景/需求规格/数量/报价周期）
        - 9个可选字段
        """
        # 创建表格
        result = self.create_ai_table(
            name="报价需求表三",
            description="钉钉对话报价需求收集表，自动同步到HubAI报价系统"
        )
        
        if "tableId" not in result:
            raise Exception(f"创建表格失败: {result}")
        
        table_id = result["tableId"]
        print(f"✅ 表格创建成功: {table_id}")
        
        # 定义所有字段
        fields = [
            # 必填字段 8个
            ("需求编号", "TEXT", None, True),
            ("客户全称", "TEXT", None, True),
            ("联系人", "TEXT", None, True),
            ("联系电话", "TEXT", None, True),
            ("使用场景", "SELECT", ["办公", "研发", "教育", "设计", "其他"], True),
            ("需求规格", "TEXTAREA", None, True),
            ("需求数量", "NUMBER", None, True),
            ("报价周期", "SELECT", ["月", "年"], True),
            
            # 可选字段 8个
            ("合同周期(月)", "NUMBER", None, False),
            ("售前支持", "CHECKBOX", ["是", "否"], False),
            ("配套方案", "CHECKBOX", ["是", "否"], False),
            ("交付服务", "CHECKBOX", ["是", "否"], False),
            ("售后服务", "CHECKBOX", ["是", "否"], False),
            ("状态", "SELECT", ["待评估", "报价中", "已报价", "已确认", "已关闭"], False),
            ("提交时间", "DATETIME", None, False),
            ("提交人", "TEXT", None, False),
            ("来源渠道", "SELECT", ["对话", "表格"], False),
            ("关联报价单", "TEXT", None, False),
        ]
        
        # 创建所有字段
        created_fields = []
        for field_name, field_type, options, required in fields:
            try:
                result = self.add_field(table_id, field_name, field_type, options, required)
                created_fields.append(result)
                status = "🔴 必填" if required else "⚪ 可选"
                print(f"  {status} {field_name} ({field_type})")
            except Exception as e:
                print(f"  ❌ 创建字段失败 {field_name}: {e}")
        
        return {
            "table_id": table_id,
            "fields_count": len(created_fields)
        }


if __name__ == "__main__":
    # 测试创建表格
    try:
        client = DingTalkAIClient()
        result = client.create_default_quote_table()
        print(f"\n✅ 创建成功！")
        print(f"   表格ID: {result['table_id']}")
        print(f"   字段数量: {result['fields_count']}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请先设置环境变量:")
        print("  export DINGTALK_APP_KEY=xxx")
        print("  export DINGTALK_APP_SECRET=xxx")
