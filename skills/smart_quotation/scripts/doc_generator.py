"""文档生成引擎 - Markdown/PDF"""
import sys
import os
# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from hubai_base.scripts.logger import HubAILogger
except ImportError:
    sys.path.append(os.path.expanduser('~/.openclaw/skills/hubai-base/scripts'))
    from logger import HubAILogger

logger = HubAILogger.get_logger("smart-quotation.doc_generator")

class DocGenerator:
    """文档生成引擎"""

    @staticmethod
    def _is_wuying_quotation(quotation_data: dict) -> bool:
        text = " ".join(str(x) for x in [
            quotation_data.get('product_name', ''),
            quotation_data.get('product_code', ''),
            quotation_data.get('category_code', ''),
            quotation_data.get('quotation_type', ''),
            *[line.get('product_name', '') or line.get('product_code', '') for line in quotation_data.get('lines', [])],
        ])
        return any(token in text for token in ['无影', 'wuying', 'WUYING', '云电脑'])

    @staticmethod
    def _money(value) -> str:
        try:
            v = float(value or 0)
            return f"¥{v:,.2f}".rstrip('0').rstrip('.')
        except Exception:
            return f"¥{value}"

    @staticmethod
    def _qty(value) -> int:
        try:
            q = int(float(value or 1))
            return q if q > 0 else 1
        except Exception:
            return 1

    @staticmethod
    def _is_terminal_line(line: dict) -> bool:
        name = str(line.get('product_name') or line.get('product_code') or line.get('product_config') or '')
        return any(token in name for token in ['终端', '无影魔方', '一体机', '方舟', '网关', '信创'])

    @staticmethod
    def _generate_wuying_unified_quotation(quotation_data: dict, title: str) -> str:
        lines_data = quotation_data.get('lines', []) or []
        cloud_lines = [x for x in lines_data if not DocGenerator._is_terminal_line(x)]
        terminal_lines = [x for x in lines_data if DocGenerator._is_terminal_line(x)]
        md = [
            f"# {title}",
            "",
            f"**报价编号**：{quotation_data.get('quotation_no', 'N/A')}",
            f"**客户**：{quotation_data.get('customer_company', quotation_data.get('customer_name', 'N/A'))}",
            "",
            "## 云电脑资源报价",
            "",
            "| 序号 | 产品名称 | 时长类型 | 产品/配置 | 数量 | 月价 | 总价（月） | 一年总价 |",
            "|---:|---|---|---|---:|---:|---:|---:|",
        ]
        cloud_month_sum = 0.0
        cloud_year_sum = 0.0
        if cloud_lines:
            for idx, line in enumerate(cloud_lines, start=1):
                qty = DocGenerator._qty(line.get('quantity'))
                month_price = float(line.get('monthly_price') or line.get('month_price') or line.get('unit_price_final') or line.get('unit_price') or 0)
                month_total = qty * month_price
                year_total = month_total * 12
                cloud_month_sum += month_total
                cloud_year_sum += year_total
                md.append(f"| {idx} | {line.get('product_name', '无影云电脑')} | {line.get('duration_label', line.get('duration_type', '-'))} | {line.get('product_config', line.get('product_code', '-'))} | {qty} | {DocGenerator._money(month_price)} | {DocGenerator._money(month_total)} | {DocGenerator._money(year_total)} |")
        else:
            md.append("| - | 无影云电脑 | - | 未选择/未匹配 | 0 | - | ¥0 | ¥0 |")
        md.extend(["", "## 无影终端报价", "", "| 序号 | 产品名称 | 产品/配置 | 数量 | 单价 | 总价 |", "|---:|---|---|---:|---:|---:|"])
        terminal_sum = 0.0
        if terminal_lines:
            for idx, line in enumerate(terminal_lines, start=1):
                qty = DocGenerator._qty(line.get('quantity'))
                unit_price = float(line.get('unit_price_final') or line.get('unit_price') or 0)
                total = qty * unit_price
                terminal_sum += total
                md.append(f"| {idx} | 无影终端 | {line.get('product_name', line.get('product_code', '-'))} | {qty} | {DocGenerator._money(unit_price)} | {DocGenerator._money(total)} |")
        else:
            md.append("| - | 无影终端 | 未选择/不需要 | 0 | ¥0 | ¥0 |")
        md.extend([
            "",
            "## 汇总",
            "",
            f"- 云电脑资源月总价：{DocGenerator._money(cloud_month_sum)}",
            f"- 云电脑资源一年总价：{DocGenerator._money(cloud_year_sum)}",
            f"- 无影终端总价：{DocGenerator._money(terminal_sum)}",
            f"- 首月合计（云电脑月总价 + 终端总价）：{DocGenerator._money(cloud_month_sum + terminal_sum)}",
            f"- 一年合计（云电脑一年总价 + 终端总价）：{DocGenerator._money(cloud_year_sum + terminal_sum)}",
            "",
            "计算口径：总价（月）= 数量 × 月价；一年总价 = 总价（月） × 12；无影终端总价 = 数量 × 单价。",
        ])
        return "\n".join(md)
    
    @staticmethod
    def generate_internal_quotation(quotation_data: dict) -> str:
        """生成内部版报价单（Markdown）"""
        if DocGenerator._is_wuying_quotation(quotation_data):
            return DocGenerator._generate_wuying_unified_quotation(quotation_data, "报价单（内部版）")
        lines = [
            "# 报价单（内部版）",
            "",
            f"**报价编号**：{quotation_data.get('quotation_no', 'N/A')}",
            f"**客户**：{quotation_data.get('customer_company', 'N/A')}",
            f"**日期**：{quotation_data.get('created_at', 'N/A')}",
            "",
            "## 产品清单",
            "",
            "| 产品 | 数量 | 原价 | 单价 | 小计 | 备注 |",
            "|------|------|------|------|------|------|"
        ]
        
        for line in quotation_data.get("lines", []):
            lines.append(
                f"| {line.get('product_code', '')} | {line.get('quantity', 0)} | "
                f"¥{line.get('unit_price_original', 0):.2f} | "
                f"¥{line.get('unit_price_final', 0):.2f} | ¥{line.get('line_amount', 0):.2f} | "
                f"{line.get('discount_note', '按报价数据源原价报价，不做折扣')} |"
            )
        
        lines.extend([
            "",
            f"**合计金额**：¥{quotation_data.get('total_amount', 0):.2f}",
            f"**毛利**：{quotation_data.get('margin_rate', 0):.1%}",
            "",
            "⚠️ 此版本为内部文件，不可直接发送给客户。"
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_customer_quotation(quotation_data: dict) -> str:
        """生成客户版报价单（Markdown，脱敏）"""
        if DocGenerator._is_wuying_quotation(quotation_data):
            return DocGenerator._generate_wuying_unified_quotation(quotation_data, "商务报价单")
        lines = [
            "# 商务报价单",
            "",
            f"**报价编号**：{quotation_data.get('quotation_no', 'N/A')}",
            f"**有效期至**：{quotation_data.get('valid_until', 'N/A')}",
            "",
            f"**客户**：{quotation_data.get('customer_company', 'N/A')}",
            "",
            "## 产品清单",
            "",
            "| 产品名称 | 数量 | 单价 | 小计 |",
            "|---------|------|------|------|"
        ]
        
        for line in quotation_data.get("lines", []):
            lines.append(
                f"| {line.get('product_code', '')} | {line.get('quantity', 0)} | "
                f"¥{line.get('unit_price_final', 0):.2f} | ¥{line.get('line_amount', 0):.2f} |"
            )
        
        lines.extend([
            "",
            f"**合计金额**：¥{quotation_data.get('total_amount', 0):.2f}（大写：{quotation_data.get('total_amount_cn', '')}）",
            "",
            "## 商务条款",
            "",
            "- **付款方式**：预付30%，发货前付清",
            "- **交付周期**：7个工作日",
            "- **保修期限**：1年标准保修",
            "",
            "---",
            "",
            "> ⚠️ **保密声明**：本报价单属于商业机密，未经授权不得向第三方披露。"
        ])
        
        return "\n".join(lines)
