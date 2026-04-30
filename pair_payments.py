#!/usr/bin/env python3
"""
Pair unpaired bank payment Todos with unpaid documents and create payments.

Data flow:
  1. Load Todos where completed_at is None and todo.name contains "payment_unpaired"
  2. Load unpaid documents:
       - outgoing bank payments (`expense_payment_unpaired`) → unpaid expenses (open + overdue)
       - incoming bank payments (`invoice_payment_unpaired`) → unpaid invoices (open + sent + overdue)
  3. For each todo, find a single matching document:
       - Prefer exact variable_symbol match
       - Else match by date window (issued_on or due_on) + remaining amount
       - Else, if date fits but currencies differ, try FX match using CNB daily rates
  4. Print pairing proposal (dry-run by default)
  5. With --execute: POST invoice payment and mark todo completed

Default is dry-run (no API writes). Use --execute to create payments.

Usage:
  uv run python pair_payments.py
  uv run python pair_payments.py --since 2026-04-01
  uv run python pair_payments.py --execute
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import config
from src.fakturoid_client import FakturoidClient
from src.fx_cnb import CnbRatesClient


PAYMENT_UNPAIRED_NEEDLE = "payment_unpaired"
TODO_EXPENSE_UNPAIRED = "expense_payment_unpaired"
TODO_INVOICE_UNPAIRED = "invoice_payment_unpaired"


def normalize_vs(value: Optional[str]) -> str:
    """Strip spaces for comparison; keep alphanumerics (VS can contain digits and letters)."""
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value)).strip().upper()


def parse_decimal(raw: Any) -> Optional[Decimal]:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return None


def _remaining_due(doc: Dict[str, Any]) -> Decimal:
    total = Decimal(str(doc.get("total") or 0))
    payments = doc.get("payments") or []
    paid = sum((Decimal(str(p.get("amount") or 0)) for p in payments), Decimal(0))
    return total - paid


def currencies_compatible(todo_cur: str, doc_cur: str) -> bool:
    if not todo_cur:
        return True
    if not doc_cur:
        return True
    return todo_cur.upper() == doc_cur.upper()


def filter_candidate_docs(
    docs: List[Dict[str, Any]],
    todo_currency: str,
    *,
    enforce_currency: bool = True,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for doc in docs:
        st = doc.get("status")
        if st == "paid":
            continue
        rem = _remaining_due(doc)
        if rem <= Decimal("0"):
            continue
        cur = (doc.get("currency") or "CZK") or "CZK"
        if enforce_currency and not currencies_compatible(todo_currency, cur):
            continue
        out.append(doc)
    return out


def _parse_iso_date(raw: Any) -> Optional[date]:
    if raw is None or raw == "":
        return None
    s = str(raw).strip()
    # ISO date or ISO datetime
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date()
        except ValueError:
            continue
    return None


def extract_payment_date(todo: Dict[str, Any]) -> Optional[date]:
    params = todo.get("params") or {}
    for k in ("paid_on", "payment_date", "date", "transaction_date", "executed_on", "posted_on"):
        d = _parse_iso_date(params.get(k))
        if d:
            return d
    d = _parse_iso_date(todo.get("created_at"))
    return d


def date_distance_days(a: Optional[date], b: Optional[date]) -> Optional[int]:
    if not a or not b:
        return None
    return abs((a - b).days)


def match_doc_for_todo(
    todo: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    amount_tolerance: Decimal,
    date_window_days: int,
    fx_client: CnbRatesClient,
    fx_tolerance_czk: Decimal,
    fx_tolerance_pct: Decimal,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Returns (reason_code, doc_or_none).
    """
    params = todo.get("params") or {}
    vs_todo = normalize_vs(params.get("variable_symbol"))
    amt_todo = parse_decimal(params.get("amount"))
    cur_todo_raw = (params.get("currency") or "").strip().upper()
    cur_todo = cur_todo_raw or "CZK"
    pay_date = extract_payment_date(todo)

    # 1) Exact variable symbol
    if vs_todo:
        vs_matches = [doc for doc in candidates if normalize_vs(doc.get("variable_symbol")) == vs_todo]
        if len(vs_matches) == 1:
            return "matched_vs", vs_matches[0]
        if len(vs_matches) > 1 and amt_todo is not None:
            narrowed = [
                doc
                for doc in vs_matches
                if abs(_remaining_due(doc) - amt_todo) <= amount_tolerance
            ]
            if len(narrowed) == 1:
                return "matched_vs_amount", narrowed[0]
            if len(narrowed) == 0:
                return "ambiguous_vs", None
            return "ambiguous_vs_amount", None
        if len(vs_matches) > 1:
            return "ambiguous_vs", None

    # 2) Date window (issued_on or due_on) + amount
    if amt_todo is not None and pay_date is not None:
        window_hits: List[Dict[str, Any]] = []
        for doc in candidates:
            issued = _parse_iso_date(doc.get("issued_on"))
            due = _parse_iso_date(doc.get("due_on"))
            dd_issued = date_distance_days(pay_date, issued)
            dd_due = date_distance_days(pay_date, due)
            dd = min([d for d in (dd_issued, dd_due) if d is not None], default=None)
            if dd is None or dd > date_window_days:
                continue
            # Direct match: require same currency (when known), and compare remaining amount
            if abs(_remaining_due(doc) - amt_todo) <= amount_tolerance and currencies_compatible(
                cur_todo_raw, (doc.get("currency") or "").strip().upper()
            ):
                window_hits.append(doc)

        if len(window_hits) == 1:
            return "matched_date_amount", window_hits[0]
        if len(window_hits) > 1:
            return "ambiguous_date_amount", None

    # 3) FX match (date fits, amount differs due to currency)
    if amt_todo is not None and pay_date is not None:
        """
        FX match:
        - allow cross-currency pairing (e.g. expense USD but payment todo in CZK)
        - compare both sides in CZK using CNB rates for pay_date
        """
        fx_hits: List[Tuple[Decimal, Dict[str, Any]]] = []
        todo_rate = fx_client.get_rate_czk_per_1(cur_todo, pay_date)
        if todo_rate is not None:
            todo_czk = amt_todo * todo_rate
            for doc in candidates:
                issued = _parse_iso_date(doc.get("issued_on"))
                due = _parse_iso_date(doc.get("due_on"))
                dd_issued = date_distance_days(pay_date, issued)
                dd_due = date_distance_days(pay_date, due)
                dd = min([d for d in (dd_issued, dd_due) if d is not None], default=None)
                if dd is None or dd > date_window_days:
                    continue

                doc_cur = ((doc.get("currency") or "") or "CZK").strip().upper() or "CZK"
                # If currencies are the same, FX step is redundant.
                if doc_cur == cur_todo:
                    continue

                doc_rate = fx_client.get_rate_czk_per_1(doc_cur, pay_date)
                if doc_rate is None:
                    continue

                doc_czk = _remaining_due(doc) * doc_rate
                diff_czk = abs(doc_czk - todo_czk)
                denom = max(abs(doc_czk), abs(todo_czk), Decimal("0.01"))
                diff_pct = (diff_czk / denom) * Decimal("100")
                if diff_czk <= fx_tolerance_czk or diff_pct <= fx_tolerance_pct:
                    fx_hits.append((diff_czk, doc))

        if len(fx_hits) == 1:
            return "matched_fx", fx_hits[0][1]
        if len(fx_hits) > 1:
            return "ambiguous_fx", None

    # 4) Amount only (conservative fallback, same currency if known)
    if amt_todo is not None:
        amount_hits = [
            doc
            for doc in candidates
            if abs(_remaining_due(doc) - amt_todo) <= amount_tolerance
            and currencies_compatible(cur_todo_raw, (doc.get("currency") or "").strip().upper())
        ]
        if len(amount_hits) == 1:
            return "matched_amount", amount_hits[0]
        if len(amount_hits) > 1:
            return "ambiguous_amount", None

    return "none", None


def build_payment_payload(
    todo: Dict[str, Any],
    doc: Dict[str, Any],
    paid_on: str,
) -> Dict[str, Any]:
    params = todo.get("params") or {}
    payload: Dict[str, Any] = {"paid_on": paid_on}
    rem = _remaining_due(doc)
    amt_todo = parse_decimal(params.get("amount"))
    doc_cur = ((doc.get("currency") or "") or "CZK").strip().upper() or "CZK"
    todo_cur_raw = (params.get("currency") or "").strip().upper()
    todo_cur = todo_cur_raw or "CZK"

    # When the payment todo is in a different currency than the document, treat todo amount
    # as native (bank account) currency and keep document amount in document currency.
    if todo_cur != doc_cur:
        payload["amount"] = str(rem)
        if amt_todo is not None:
            payload["native_amount"] = str(amt_todo)
    else:
        if amt_todo is not None and amt_todo <= rem + Decimal("0.0001"):
            payload["amount"] = str(amt_todo)
    # Optional: tie to bank account from email import
    bid = params.get("bank_account_id")
    if bid not in (None, ""):
        try:
            payload["bank_account_id"] = int(bid)
        except (TypeError, ValueError):
            pass
    vs = params.get("variable_symbol")
    if vs:
        payload["variable_symbol"] = str(vs).strip()
    payload["mark_document_as_paid"] = True
    return payload


def run(
    execute: bool,
    amount_tolerance: Decimal,
    paid_on: Optional[str],
    complete_todos: bool,
    since: Optional[str],
    date_window_days: int,
    fx_tolerance_czk: Decimal,
    fx_tolerance_pct: Decimal,
) -> int:
    client = FakturoidClient(config)
    if not client.test_connection():
        print("❌ Fakturoid connection failed. Check .env credentials.")
        return 1

    todos = client.list_todos(since=since)
    uncompleted = [t for t in todos if not t.get("completed_at")]
    names = Counter((t.get("name") or "").strip() for t in uncompleted)
    unpaired = [
        t
        for t in uncompleted
        if PAYMENT_UNPAIRED_NEEDLE in (t.get("name") or "").lower()
    ]

    # Load candidates for both directions. We'll pick based on todo.name.
    expenses = client.list_unpaid_expenses()
    expense_candidates = filter_candidate_docs(expenses, "", enforce_currency=False)
    invoices = client.list_unpaid_invoices()
    invoice_candidates = filter_candidate_docs(invoices, "", enforce_currency=False)

    print("Uncompleted todos by name:")
    for name, cnt in sorted(names.items(), key=lambda x: (-x[1], x[0])):
        if not name:
            continue
        print(f"  - {name}: {cnt}")

    print()
    print(f"Found {len(unpaired)} unpaired payment todo(s) (name contains '{PAYMENT_UNPAIRED_NEEDLE}').")
    print(f"Found {len(expense_candidates)} unpaid expense(s) with remaining balance.")
    print(f"Found {len(invoice_candidates)} unpaid invoice(s) with remaining balance.\n")

    matched = 0
    skipped = 0
    used_expense_ids: set = set()
    used_invoice_ids: set = set()
    fx = CnbRatesClient()

    for todo in sorted(unpaired, key=lambda x: x.get("created_at") or ""):
        tid = todo.get("id")
        params = todo.get("params") or {}
        cur = (params.get("currency") or "").strip().upper()
        d = extract_payment_date(todo)
        tname = (todo.get("name") or "").strip()

        if tname == TODO_EXPENSE_UNPAIRED:
            base_pool = expense_candidates
            used = used_expense_ids
            kind = "expense"
        elif tname == TODO_INVOICE_UNPAIRED:
            base_pool = invoice_candidates
            used = used_invoice_ids
            kind = "invoice"
        else:
            print(f"  ⏭️  SKIP (unsupported_todo_name)  Todo #{tid} ({tname})")
            skipped += 1
            continue

        pool = [
            doc
            for doc in filter_candidate_docs(base_pool, cur, enforce_currency=False)
            if doc["id"] not in used
        ]

        reason, doc = match_doc_for_todo(
            todo,
            pool,
            amount_tolerance=amount_tolerance,
            date_window_days=date_window_days,
            fx_client=fx,
            fx_tolerance_czk=fx_tolerance_czk,
            fx_tolerance_pct=fx_tolerance_pct,
        )

        ptxt = (
            f"Todo #{tid} ({todo.get('name')}): "
            f"VS={params.get('variable_symbol')} amt={params.get('amount')} {params.get('currency', '')} "
            f"date={d.isoformat() if d else 'n/a'}"
        )

        if doc is None:
            print(f"  ⏭️  SKIP ({reason})  {ptxt}")
            skipped += 1
            continue

        did = doc["id"]
        num = doc.get("number") or doc.get("custom_id") or doc.get("original_number")
        rem = _remaining_due(doc)
        print(f"  ✓ {reason}: {ptxt}")
        print(
            f"      → {kind.title()} #{did} ({num}) remaining={rem} {doc.get('currency')} "
            f"issued_on={doc.get('issued_on')} due_on={doc.get('due_on')}"
        )

        effective_paid_on = paid_on or (d.isoformat() if d else date.today().isoformat())

        if execute:
            try:
                payload = build_payment_payload(todo, doc, effective_paid_on)
                if kind == "invoice":
                    client.create_invoice_payment(did, payload)
                    used_invoice_ids.add(did)
                else:
                    client.create_expense_payment(did, payload)
                    used_expense_ids.add(did)
                matched += 1
                print(f"      ✅ Payment created.")
                if complete_todos:
                    client.toggle_todo_completion(int(tid))
                    print(f"      ✅ Todo #{tid} marked completed.")
            except Exception as ex:
                print(f"      ❌ Error: {ex}")
                skipped += 1
        else:
            print(f"      (dry-run) would POST {kind} payment paid_on={effective_paid_on} and complete todo #{tid}")
            print(f"      (dry-run) payload: {json.dumps(build_payment_payload(todo, doc, effective_paid_on), ensure_ascii=False)}")
            used.add(did)
            matched += 1

    print()
    if execute:
        print(f"Done. Payments created: {matched}, skipped/errors: {skipped}")
    else:
        print(f"Dry-run finished. Would pair up to {matched} payment(s). Run with --execute to apply.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pair Fakturoid unpaired payment todos with unpaid invoices.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Create invoice payments and complete todos (default: dry-run only)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Fetch todos created after this ISO datetime (passed to Fakturoid todos.json since=...)",
    )
    parser.add_argument(
        "--amount-tolerance",
        type=str,
        default="0.02",
        help="Max difference for amount matching (same currency), default 0.02",
    )
    parser.add_argument(
        "--paid-on",
        type=str,
        default=None,
        help="Force payment date YYYY-MM-DD (default: derived from todo params/created_at)",
    )
    parser.add_argument(
        "--date-window-days",
        type=int,
        default=3,
        help="Max day distance between payment date and invoice issued_on/due_on, default 3",
    )
    parser.add_argument(
        "--fx-tolerance-czk",
        type=str,
        default="10",
        help="FX match tolerance in CZK (after conversion), default 10",
    )
    parser.add_argument(
        "--fx-tolerance-pct",
        type=str,
        default="1.0",
        help="FX match tolerance in percent (after conversion), default 1.0",
    )
    parser.add_argument(
        "--no-complete-todo",
        action="store_true",
        help="After payment, do not mark the todo as completed",
    )
    args = parser.parse_args()

    try:
        tol = Decimal(args.amount_tolerance)
    except InvalidOperation:
        print("Invalid --amount-tolerance")
        return 1

    try:
        fx_tol_czk = Decimal(args.fx_tolerance_czk)
        fx_tol_pct = Decimal(args.fx_tolerance_pct)
    except InvalidOperation:
        print("Invalid FX tolerance")
        return 1

    if args.execute:
        print("⚠️  EXECUTE MODE: will create payments in Fakturoid.\n")
    else:
        print("ℹ️  DRY-RUN: no payments will be created. Use --execute to apply.\n")

    return run(
        execute=args.execute,
        amount_tolerance=tol,
        paid_on=args.paid_on,
        complete_todos=not args.no_complete_todo,
        since=args.since,
        date_window_days=args.date_window_days,
        fx_tolerance_czk=fx_tol_czk,
        fx_tolerance_pct=fx_tol_pct,
    )


if __name__ == "__main__":
    sys.exit(main())
