"""Uniform behavior-fact snapshots per language extractor.

Phase 0: pins current output exactly so later phases (Python behavior
rows, generic evidence) cannot silently change other languages. The
contract test pins the other direction: every emitted behavior kind must
be declared in `BEHAVIOR_ROW_KINDS`.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_code_relationships_facts", ROOT / "scripts" / "code_relationships.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PY_VALIDATION = '''"""Order quantity validation."""

from shop.orders.models import Order
from . import helpers


class OrderValidator:
    """Validates order quantities before checkout."""

    def reject_zero_quantity(self, order):
        """Reject zero quantities but keep positive quantities working."""
        assert order is not None
        if order.quantity == 0:
            raise ValueError("quantity must be positive")
        helpers.log("checked")
        return True
'''

TSX_HANDLER = '''import { useState } from "react";

export function OrderPage({ order }) {
  const [error, setError] = useState(null);
  async function handleSubmit() {
    const ok = await validate(order);
    if (!ok) {
      setError("quantity must be positive");
    }
  }
  return (
    <form onSubmit={handleSubmit}>
      {error && <aside>{error}</aside>}
    </form>
  );
}
'''

JAVA_GUARD = """package shop.orders;

public class OrderValidator {
    public boolean rejectZeroQuantity(Order order) {
        if (order.quantity == 0) {
            throw new IllegalArgumentException("quantity must be positive");
        }
        return true;
    }
}
"""

GO_GUARD = """package orders

import "errors"

func RejectZeroQuantity(quantity int) error {
	if quantity == 0 {
		return errors.New("quantity must be positive")
	}
	return nil
}
"""


class BehaviorFactSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def rows(self, facts):
        return sorted(
            (row["kind"], row["value"]) for row in facts.get("behavior", [])
        )

    def test_python_snapshot(self) -> None:
        facts = self.module.extract(
            Path("shop/orders/service.py"), Path("."), PY_VALIDATION
        )
        self.assertEqual(
            sorted((row["kind"], row["value"]) for row in facts["definitions"]),
            [("classdef", "OrderValidator"), ("functiondef", "reject_zero_quantity")],
        )
        self.assertEqual(
            sorted((row["kind"], row["value"]) for row in facts["imports"]),
            [("import", "."), ("import", "shop.orders.models")],
        )
        self.assertEqual(facts["registrations"], [])
        # Phase 0 gap, pinned: the AST parser emits no behavior rows yet.
        # Phase 1 must populate import-binding/call/call-result/raise rows.
        self.assertEqual(facts["behavior"], [])

    def test_tsx_snapshot(self) -> None:
        facts = self.module.extract(
            Path("shop/ui/order_page.tsx"), Path("."), TSX_HANDLER
        )
        self.assertEqual(
            self.rows(facts),
            [
                ("call", "return"),
                ("call", "setError"),
                ("call", "useState"),
                ("call", "validate"),
                ("call-result", "ok"),
                ("import-binding", "useState"),
                ("render-use", "error"),
                ("state-binding", "error"),
                ("state-write", "error"),
            ],
        )

    def test_java_and_go_snapshots(self) -> None:
        java = self.module.extract(
            Path("shop/orders/OrderValidator.java"), Path("."), JAVA_GUARD
        )
        go = self.module.extract(
            Path("shop/orders/service.go"), Path("."), GO_GUARD
        )
        self.assertEqual(self.rows(java), [])
        self.assertEqual(self.rows(go), [])

    def test_emitted_kinds_stay_within_declared_contract(self) -> None:
        fixtures = (
            ("a.py", PY_VALIDATION),
            ("a.tsx", TSX_HANDLER),
            ("a.java", JAVA_GUARD),
            ("a.go", GO_GUARD),
        )
        for name, text in fixtures:
            with self.subTest(fixture=name):
                facts = self.module.extract(Path(name), Path("."), text)
                for row in facts.get("behavior", []):
                    self.assertIn(row["kind"], self.module.BEHAVIOR_ROW_KINDS)


if __name__ == "__main__":
    unittest.main()
