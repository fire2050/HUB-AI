from .price_engine import calculate_price, generate_quotation_lines
from .rule_validator import RuleValidator
from .route_engine import RouteEngine
from .doc_generator import DocGenerator
from .approval_engine import ApprovalEngine
from .requirement_card import generate_requirement_card
from .quotation_coordinator import QuotationCoordinator
from .session_manager import SessionManager
from .cross_product import CrossProductQuotation

__all__ = [
    'calculate_price',
    'generate_quotation_lines',
    'RuleValidator',
    'RouteEngine',
    'DocGenerator',
    'ApprovalEngine',
    'generate_requirement_card',
    'QuotationCoordinator',
    'SessionManager',
    'CrossProductQuotation'
]
__version__ = '1.1.0'  # 多产品架构增强版
