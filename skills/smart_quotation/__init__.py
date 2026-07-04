"""HubAI 智能报价核心引擎包"""

from .scripts.price_engine import calculate_price
from .scripts.rule_validator import RuleValidator
from .scripts.route_engine import RouteEngine
from .scripts.doc_generator import DocGenerator
from .scripts.approval_engine import ApprovalEngine
from .scripts.requirement_card import generate_requirement_card

__version__ = "1.0.0"
__all__ = [
    'calculate_price',
    'RuleValidator',
    'RouteEngine',
    'DocGenerator',
    'ApprovalEngine',
    'generate_requirement_card'
]
