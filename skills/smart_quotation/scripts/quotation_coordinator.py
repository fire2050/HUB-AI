"""报价协调器 - 统一报价入口，负责产品检测、会话管理、Skill 调度
核心原则：无数据不编造，宁可报不了价，绝不估算数据
"""
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# === 路径解析：兼容软链接环境 ===
_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILLS_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))  # 到 skills 根目录

# 尝试多种路径加载底座模块
_BASE_PATHS = [
    os.path.join(_SKILLS_ROOT, 'hubai_base', 'scripts'),
    os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'),
    os.path.expanduser('~/hubai/skills/hubai_base/scripts'),
]
for _p in _BASE_PATHS:
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from product_router import ProductRouter
    from logger import HubAILogger
    from quotation_flow import classify_quotation_entry, quotation_flow_prompt
except ImportError as e:
    # 兜底：如果底座模块加载失败，记录错误但不崩溃
    print(f"[WARNING] 底座模块加载失败: {e}", file=sys.stderr)
    ProductRouter = None
    HubAILogger = None
    classify_quotation_entry = None
    quotation_flow_prompt = None

logger = HubAILogger.get_logger("smart-quotation.coordinator") if HubAILogger else None


def _safe_log(msg: str):
    """安全日志：logger 不可用时打印到 stderr"""
    if logger:
        logger.info(msg)
    else:
        print(f"[INFO] {msg}", file=sys.stderr)


class QuotationCoordinator:
    """报价协调器 - 统一入口
    
    安全规则：
    1. 无产品配置 → 拒绝报价，提示联系管理员
    2. 无价格数据 → 拒绝报价，提示补充价格
    3. 无库存数据 → 报价+标注"库存待确认"
    4. 无折扣策略 → 按原价计算，标注"无折扣"
    """
    
    def __init__(self):
        self.sessions = {}  # 会话管理：{session_id: session_data}
        self.router = None
        
        # 初始化产品路由器
        if ProductRouter:
            _config_dir = self._find_products_config_dir()
            if _config_dir:
                try:
                    self.router = ProductRouter(config_dir=_config_dir)
                    _safe_log(f"产品路由器初始化成功: {_config_dir}")
                except Exception as e:
                    _safe_log(f"产品路由器初始化失败: {e}")
    
    def _find_products_config_dir(self) -> Optional[str]:
        """查找产品配置目录"""
        candidates = [
            os.path.join(_SKILLS_ROOT, 'hubai_base', 'config', 'products'),
            os.path.expanduser('~/.openclaw/skills/hubai-base/config/products'),
            os.path.expanduser('~/hubai/skills/hubai_base/config/products'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None
    
    def handle_message(self, session_id: str, user_message: str) -> dict:
        """处理用户消息（统一入口）"""
        _safe_log(f"Handling message: session={session_id}, msg={user_message[:50]}...")
        
        # 1. 获取或创建会话
        session = self._get_or_create_session(session_id)
        
        # 2. 产品路由器不可用时
        if not self.router:
            return self._error_response(
                "SYSTEM_NOT_READY",
                "报价系统初始化失败",
                "产品路由器模块加载异常，请联系管理员检查配置",
                {"action": "联系管理员"}
            )
        
        # 3. 检测产品（如果尚未确定）
        if not session.get('product_code'):
            products = self.router.detect_product(user_message)
            if products:
                session['product_code'] = products[0].code
                session['product_name'] = products[0].name
                session['skill_name'] = products[0].skill_name
                _safe_log(f"Product detected: {products[0].code}")
                return {
                    "success": True,
                    "action": "ask_quotation_type",
                    "product_code": products[0].code,
                    "product_name": products[0].name,
                    "message": f"已识别产品：{products[0].name}\n\n报价前请先确认本次是【单品查询】还是【方案报价】：\n\n1️⃣ 单品查询：按云产品资源配置/硬件设备/产品名称直接查价。\n2️⃣ 方案报价：需要先补齐需求清单必要项，再生成完整报价。\n\n说明：系统按报价数据源原价报价，不做折扣。"
                }
            else:
                # 未检测到产品，返回引导话术
                all_products = []
                try:
                    all_products = [p.name for p in self.router.get_all_products()]
                except:
                    pass
                return {
                    "success": True,
                    "action": "ask_product",
                    "available_products": all_products,
                    "message": "您好！我可以为您提供以下产品的报价：\n\n" +
                               ("\n".join([f"• {p}" for p in all_products]) if all_products else "• 云计算\n• 无影云电脑") +
                               "\n\n请告诉我您需要哪个产品的报价？"
                }
        
        # 4. 产品已确定，统一使用报价入口分流器确认报价类型
        quotation_type = session.get('quotation_type')
        if not quotation_type:
            if classify_quotation_entry:
                decision = classify_quotation_entry(user_message, session.get('collected_data', {}))
                session['flow_decision'] = decision.to_dict()
                if decision.flow_type == 'single_item':
                    session['quotation_type'] = '单品查询'; quotation_type = '单品查询'
                elif decision.flow_type == 'requirement_p0':
                    session['quotation_type'] = '方案报价'; quotation_type = '方案报价'
                else:
                    return {
                        "success": True,
                        "action": "ask_quotation_type",
                        "product_code": session['product_code'],
                        "product_name": session['product_name'],
                        "flow_decision": decision.to_dict(),
                        "message": quotation_flow_prompt() if quotation_flow_prompt else "请先确认：本次是【单品查询】还是【方案报价】？"
                    }
            else:
                if any(k in user_message for k in ['单品查询', '单品', '查价', '查一下', '查多少钱']):
                    session['quotation_type'] = '单品查询'; quotation_type = '单品查询'
                elif any(k in user_message for k in ['方案报价', '方案', '整套', '全套']):
                    session['quotation_type'] = '方案报价'; quotation_type = '方案报价'
                else:
                    return {
                        "success": True,
                        "action": "ask_quotation_type",
                        "product_code": session['product_code'],
                        "product_name": session['product_name'],
                        "message": "请先确认：本次是【单品查询】还是【方案报价】？\n\n1️⃣ 单品查询：按配置/产品名称直接查价。\n2️⃣ 方案报价：补齐需求清单后生成完整报价。\n\n说明：系统按报价数据源原价报价，不做折扣。"
                    }

        # 5. 更新会话数据
        self._extract_fields(session, user_message)

        # 6. 检查是否包含报价关键词，尝试直接报价
        if self._is_quotation_request(user_message) or '查价' in user_message or '查一下' in user_message:
            return self._try_generate_quotation(session, quotation_type)

        # 7. 继续收集需求
        return {
            "success": True,
            "action": "collecting_requirement",
            "product_code": session['product_code'],
            "product_name": session['product_name'],
            "collected_data": session.get('collected_data', {}),
            "message": "收到，请继续提供需求信息..."
        }
    
    def _try_generate_quotation(self, session: dict, quotation_type: str = None) -> dict:
        """尝试生成报价（带完整数据校验）"""
        product_code = session.get('product_code')
        collected = session.get('collected_data', {})
        
        # === 安全检查 1：产品 Skill 是否存在 ===
        skill_path = self._find_product_skill_path(product_code)
        if not skill_path:
            return self._error_response(
                "SKILL_NOT_FOUND",
                f"产品 '{product_code}' 的报价模块未找到",
                "该产品可能尚未部署或配置不完整，请联系管理员",
                {"product_code": product_code}
            )
        
        # === 安全检查 2：价格引擎是否存在 ===
        price_engine_path = os.path.join(skill_path, 'scripts', 'price_engine.py')
        if not os.path.exists(price_engine_path):
            return self._error_response(
                "PRICE_ENGINE_MISSING",
                f"产品 '{product_code}' 的价格引擎未配置",
                "价格计算模块缺失，无法生成报价。请联系产品管理员补充配置",
                {"product_code": product_code, "missing": "price_engine.py"}
            )
        
        # === 安全检查 3：尝试加载价格引擎 ===
        try:
            price_engine = self._load_price_engine(skill_path)
            if not price_engine:
                return self._error_response(
                    "PRICE_ENGINE_LOAD_FAILED",
                    "价格引擎加载失败",
                    "价格计算模块加载异常，请检查模块代码",
                    {"product_code": product_code}
                )
        except Exception as e:
            return self._error_response(
                "PRICE_ENGINE_ERROR",
                "价格引擎执行异常",
                str(e),
                {"product_code": product_code}
            )
        
        # === 安全检查 4：尝试计算价格 ===
        try:
            # 优先调用产品 Skill 的 quote()（支持单品/方案模式）；兼容旧 calculate_price
            requirement = self._build_requirement(collected)
            if quotation_type:
                requirement['quotation_type'] = quotation_type
            if hasattr(price_engine, 'WuyingPCPriceEngine') and hasattr(price_engine.WuyingPCPriceEngine, 'quote'):
                result = price_engine.WuyingPCPriceEngine.quote(requirement)
            else:
                result = price_engine.calculate_price(**requirement)

            if not result.get('success', True):
                # 时长类型缺失不是系统错误，而是单品查询的必要选择项，直接追问用户。
                if result.get('error_code') == 'DURATION_TYPE_REQUIRED':
                    details = result.get('details', {}) if isinstance(result.get('details'), dict) else {}
                    options = details.get('duration_options', [])
                    option_lines = "\n".join([f"| {idx} | {x.get('label')} |" for idx, x in enumerate(options, start=1)])
                    return {
                        "success": True,
                        "action": "ask_duration_type",
                        "product_code": product_code,
                        "product_name": session.get('product_name'),
                        "quotation_type": "单品查询",
                        "duration_options": options,
                        "message": "该产品/配置存在多个时长类型，请先选择一个时长类型后再报价：\n\n"
                                   "| 序号 | 时长类型 |\n"
                                   "|---:|---|\n"
                                   f"{option_lines}\n\n"
                                   "您可以直接回复：120小时、200小时、不限时长1小时休眠、不限时长或教育办公。"
                    }

                # 价格引擎返回了错误
                return self._error_response(
                    result.get('error_code', 'PRICE_CALC_FAILED'),
                    result.get('error_message', '价格计算失败'),
                    result.get('details', {}),
                    {"product_code": product_code}
                )
            
            # 生成报价单
            return {
                "success": True,
                "action": "quotation_generated",
                "product_code": product_code,
                "product_name": session.get('product_name'),
                "quotation_no": f"Q{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "quotation_data": result,
                "flow_decision": session.get('flow_decision'),
                "message": self._format_quotation_message(result, session)
            }
            
        except Exception as e:
            return self._error_response(
                "QUOTATION_EXCEPTION",
                "报价生成异常",
                f"计算过程中发生错误: {str(e)}",
                {"product_code": product_code}
            )
    
    def _load_price_engine(self, skill_path: str):
        """动态加载产品 Skill 的价格引擎"""
        import importlib.util
        engine_file = os.path.join(skill_path, 'scripts', 'price_engine.py')
        if not os.path.exists(engine_file):
            return None
        
        spec = importlib.util.spec_from_file_location(
            "price_engine", engine_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def _find_product_skill_path(self, product_code: str) -> Optional[str]:
        """查找产品 Skill 路径"""
        candidates = [
            os.path.join(_SKILLS_ROOT, f'product-{product_code}'),
            os.path.expanduser(f'~/.openclaw/skills/product-{product_code}'),
            os.path.expanduser(f'~/hubai/skills/product-{product_code}'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None
    
    def _build_requirement(self, collected: dict) -> dict:
        """从收集的数据构建需求参数"""
        # 简化：直接传递收集到的数据
        return collected
    
    def _is_quotation_request(self, message: str) -> bool:
        """判断是否为报价请求"""
        keywords = ['报价', '多少钱', '价格', '预算', '费用', '算一下']
        return any(kw in message for kw in keywords)
    
    def _error_response(self, code: str, title: str, detail: str, extra: dict = None) -> dict:
        """标准化错误响应"""
        return {
            "success": False,
            "error_code": code,
            "error_title": title,
            "error_detail": detail,
            "message": f"❌ {title}\n\n{detail}\n\n"
                       f"系统不会进行以下操作：\n"
                       f"❌ 估算价格\n"
                       f"❌ 假设折扣\n"
                       f"❌ 编造数据\n\n"
                       f"请补充正确数据后再试，或联系管理员。",
            **(extra or {})
        }
    
    def _format_quotation_message(self, result: dict, session: dict) -> str:
        """格式化报价消息"""
        if result.get('quote_type') in ('single_item', 'solution') and result.get('message'):
            return result['message']

        lines = []
        lines.append(f"✅ 报价单已生成")
        lines.append(f"")
        lines.append(f"产品：{session.get('product_name', '未知')}")
        
        if 'unit_price_monthly' in result:
            lines.append(f"单价：¥{result['unit_price_monthly']}/点/月")
        if 'total_amount' in result:
            lines.append(f"总价（原价）：¥{result['total_amount']}")
        if 'discount_rate' in result:
            lines.append(f"折扣策略：{result.get('discount_note', '按报价数据源原价报价，不做折扣')}")
        if 'data_source' in result:
            lines.append(f"数据来源：{result['data_source']}")
        
        return "\n".join(lines)
    
    def _get_or_create_session(self, session_id: str) -> dict:
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'session_id': session_id,
                'product_code': None,
                'product_name': None,
                'skill_name': None,
                'collected_data': {},
                'created_at': datetime.now().isoformat()
            }
        return self.sessions[session_id]
    
    def _extract_fields(self, session: dict, user_message: str):
        """从用户消息中提取字段值（简化版）"""
        # 简单关键字匹配提取
        collected = session.get('collected_data', {})

        if session.get('quotation_type'):
            collected['quotation_type'] = session['quotation_type']

        # 单品查询：保留用户原始查询文本，价格引擎会按配置/产品名称模糊查价
        if session.get('quotation_type') == '单品查询':
            q = user_message
            for token in ['单品查询', '单品', '查价', '查一下', '查多少钱', '报价', '价格', '多少钱']:
                q = q.replace(token, ' ')
            q = ' '.join(q.split())
            if q:
                collected['query'] = q
            duration_aliases = {
                '120h': ['120小时', '120h', 'D21', 'd21'],
                '200h': ['200小时', '200h', 'D22图形', 'D22国内图形', '图形200小时'],
                'unlimited_1h_sleep': ['1小时休眠', '办公1小时休眠', 'D22不限时', 'D21不限时'],
                'unlimited': ['D23', 'd23', '无强制休眠'],
                'education': ['教育办公', 'D1', 'd1'],
            }
            for code, aliases in duration_aliases.items():
                if any(alias in user_message for alias in aliases):
                    collected['duration_type'] = code
                    break

        # 提取客户公司名称、联系人（轻量规则，避免方案报价明明给了基础信息却被判缺失）
        import re
        company_patterns = [
            r'客户(?:公司|单位)?(?:是|为|：|:)\s*([^，,。；;\s]+(?:公司|集团|学校|医院|科技|有限公司))',
            r'([^，,。；;\s]+(?:有限公司|公司|集团|学校|医院))',
        ]
        for pattern in company_patterns:
            match = re.search(pattern, user_message)
            if match:
                collected['customer_company'] = match.group(1).strip()
                break

        contact_patterns = [
            r'联系人(?:是|为|：|:)?\s*([^，,。；;\s]+)',
            r'对接人(?:是|为|：|:)?\s*([^，,。；;\s]+)',
        ]
        for pattern in contact_patterns:
            match = re.search(pattern, user_message)
            if match:
                collected['contact_person'] = match.group(1).strip()
                break

        # 尝试提取使用场景
        scenario_options = ['安全办公', '教育培训', '研发设计', '数字人&媒体运营', 'AI agents', '其他']
        matched_scenarios = [x for x in scenario_options if x in user_message]
        if matched_scenarios:
            collected['usage_scenario'] = matched_scenarios

        # 方案报价必要项：休眠方式必须在报价前询问并确认
        for policy in ['支持24小时开机', '无强制休眠策略']:
            if policy in user_message:
                collected['sleep_policy'] = policy
                break

        # 尝试提取部署规模
        if '点' in user_message or '个' in user_message or '台' in user_message:
            match = re.search(r'(\d+)\s*[点个台]', user_message)
            if match:
                qty = int(match.group(1))
                collected['quantity'] = qty
                if qty < 10:
                    collected['deployment_scale'] = '10点以下'
                elif qty <= 50:
                    collected['deployment_scale'] = '10-50点'
                elif qty <= 100:
                    collected['deployment_scale'] = '50-100点'
                elif qty <= 300:
                    collected['deployment_scale'] = '100-300点'
                else:
                    collected['deployment_scale'] = '300点以上'
        
        # 尝试提取云产品资源配置（兼容字段名 performance_level）
        performance_keywords = {
            '办公型标准型-4核8G内存30M带宽（支持24小时开机）': '办公型标准型-4核8G内存30M带宽（支持24小时开机）',
            '办公型标准型-4核8G内存30M带宽（无强制休眠策略）': '办公型标准型-4核8G内存30M带宽（无强制休眠策略）',
            '办公型标准': '办公型标准型-4核8G内存30M带宽（支持24小时开机）',
            '办公型增强': '办公型增强型-6核12G内存30M带宽（支持24小时开机）',
            '办公型高级': '办公型高级型-8核16G内存30M带宽（支持24小时开机）',
            '图形型': '图形型-8核16G内存2G显存(5880)30M带宽（支持24小时开机）',
        }
        for kw, level in performance_keywords.items():
            if kw in user_message:
                collected['performance_level'] = level
                break

        # 简单提取云盘配置
        for storage in ['50GB/用户', '100GB/用户', '200GB/用户', '500GB/用户', '1TB/用户', '不需要']:
            if storage.replace('/用户','') in user_message or storage in user_message:
                collected['cloud_storage'] = storage
                break

        session['collected_data'] = collected
    
    def generate_quotation(self, session_id: str) -> dict:
        """生成报价（外部调用入口）"""
        session = self.sessions.get(session_id)
        if not session:
            return self._error_response(
                "SESSION_NOT_FOUND", "会话不存在", "请重新开始报价流程"
            )
        
        product_code = session.get('product_code')
        if not product_code:
            return self._error_response(
                "PRODUCT_NOT_SET", "产品未确定", "请先选择产品类型"
            )
        
        return self._try_generate_quotation(session)
