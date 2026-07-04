from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.security import get_user  # noqa: E402
from app.service import answer_query  # noqa: E402

CASES = [
    ("u_sales_zhang", "查我上个月销售额", "metric"),
    ("u_sales_zhang", "各部门销售额对比", "permission_denied"),
    ("u_finance_admin", "各部门销售额对比", "compare"),
    ("u_finance_admin", "看看有没有异常预警", "alerts"),
]


def main() -> None:
    for user_id, message, expected in CASES:
        result = answer_query(message, get_user(user_id))
        actual = result["intent"]
        assert actual == expected, f"{user_id=} {message=} expected {expected}, got {actual}"
        print(f"OK {user_id}: {message} -> {actual}")
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
