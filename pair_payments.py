#!/usr/bin/env python3
"""
Pair unpaired bank payment Todos with unpaid documents and create payments.

Data flow:
  1. Load Todos where completed_at is None and todo.name contains "payment_unpaired"
  2. Load unpaid documents:
       - outgoing bank payments (`expense_payment_unpaired`) → unpaid expenses (open + overdue)
       - incoming bank payments (`invoice_payment_unpaired`) → unpaid invoices (open + sent + overdue)
  3. Build a proposal table for all unpaid expenses:
       - Prefer exact variable_symbol match
       - Else match by date window (issued_on or due_on) + remaining amount
       - Else, if date fits but currencies differ, try FX match using CNB daily rates
  4. Print pairing proposal (dry-run by default)
  5. With --execute:
       - --confirm-all: apply all unambiguous matches
       - --interactive: confirm one-by-one

Default is dry-run (no API writes). Use --execute to create payments.

Usage:
  uv run python pair_payments.py
  uv run python pair_payments.py --since 1.1.2026
  uv run python pair_payments.py --since 2026-04-01 --execute --confirm-all
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter
from datetime import date, datetime
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


def parse_since_argument(raw: str) -> str:
    """
    Parse --since for Fakturoid API (ISO 8601 datetime).

    Accepts:
      - 2026-01-01 or 2026-01-01T12:00:00
      - 1.1.2026, 01.01.2026 (Czech day.month.year)
      - 1/1/2026
    """
    s = raw.strip()
    if not s:
        raise ValueError("empty --since")

    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        if "T" in s:
            return s
        return f"{s}T00:00:00"

    m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{2,4})$", s)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000 if year < 70 else 1900
        dt = date(year, month, day)
        return datetime.combine(dt, datetime.min.time()).isoformat()

    raise ValueError(
        f"neznámý formát data: {raw!r} — použijte např. 1.1.2026 nebo 2026-01-01"
    )


def setup_pairing_logger(log_path: str = "logs/pair_payments.log") -> logging.Logger:
    logger = logging.getLogger("pair_payments")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(p, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


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


def _doc_date_candidates(doc: Dict[str, Any]) -> List[date]:
    out: List[date] = []
    for k in ("issued_on", "due_on"):
        d = _parse_iso_date(doc.get(k))
        if d:
            out.append(d)
    return out


def _best_doc_date_distance(pay_date: Optional[date], doc: Dict[str, Any]) -> Optional[int]:
    if not pay_date:
        return None
    ds = _doc_date_candidates(doc)
    if not ds:
        return None
    return min(abs((pay_date - d).days) for d in ds)


def _doc_currency(doc: Dict[str, Any]) -> str:
    return ((doc.get("currency") or "") or "CZK").strip().upper() or "CZK"


def score_todo_for_doc(
    todo: Dict[str, Any],
    doc: Dict[str, Any],
    *,
    amount_tolerance: Decimal,
    date_window_days: int,
    fx_client: CnbRatesClient,
    fx_tolerance_czk: Decimal,
    fx_tolerance_pct: Decimal,
) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (reason_code, details).

    reason_code is one of:
      matched_vs_amount, matched_vs, matched_date_amount, matched_fx, matched_amount, none
    """
    params = todo.get("params") or {}
    vs_todo = normalize_vs(params.get("variable_symbol"))
    amt_todo = parse_decimal(params.get("amount"))
    todo_cur_raw = (params.get("currency") or "").strip().upper()
    todo_cur = todo_cur_raw or "CZK"
    pay_date = extract_payment_date(todo)

    doc_vs = normalize_vs(doc.get("variable_symbol"))
    doc_cur = _doc_currency(doc)
    rem = _remaining_due(doc)
    dd = _best_doc_date_distance(pay_date, doc)

    details: Dict[str, Any] = {
        "todo_id": todo.get("id"),
        "todo_name": todo.get("name"),
        "todo_amount": str(amt_todo) if amt_todo is not None else None,
        "todo_currency": todo_cur_raw or None,
        "todo_date": pay_date.isoformat() if pay_date else None,
        "todo_vs": params.get("variable_symbol"),
        "doc_id": doc.get("id"),
        "doc_number": doc.get("number") or doc.get("original_number") or doc.get("custom_id"),
        "doc_currency": doc_cur,
        "doc_remaining": str(rem),
        "doc_issued_on": doc.get("issued_on"),
        "doc_due_on": doc.get("due_on"),
        "date_distance_days": dd,
    }

    # 1) VS match
    if vs_todo and doc_vs and vs_todo == doc_vs:
        if amt_todo is not None and abs(rem - amt_todo) <= amount_tolerance and currencies_compatible(todo_cur_raw, doc_cur):
            return "matched_vs_amount", details
        return "matched_vs", details

    # 2) Date+amount match (same currency if known)
    if amt_todo is not None and dd is not None and dd <= date_window_days:
        if abs(rem - amt_todo) <= amount_tolerance and currencies_compatible(todo_cur_raw, doc_cur):
            return "matched_date_amount", details

    # 3) FX match (cross-currency, compare in CZK)
    if amt_todo is not None and dd is not None and dd <= date_window_days and todo_cur != doc_cur:
        todo_rate = fx_client.get_rate_czk_per_1(todo_cur, pay_date) if pay_date else None
        doc_rate = fx_client.get_rate_czk_per_1(doc_cur, pay_date) if pay_date else None
        if todo_rate is not None and doc_rate is not None:
            todo_czk = amt_todo * todo_rate
            doc_czk = rem * doc_rate
            diff_czk = abs(doc_czk - todo_czk)
            denom = max(abs(doc_czk), abs(todo_czk), Decimal("0.01"))
            diff_pct = (diff_czk / denom) * Decimal("100")
            details["fx_diff_czk"] = str(diff_czk)
            details["fx_diff_pct"] = str(diff_pct)
            details["fx_todo_rate_czk_per_1"] = str(todo_rate)
            details["fx_doc_rate_czk_per_1"] = str(doc_rate)
            if diff_czk <= fx_tolerance_czk or diff_pct <= fx_tolerance_pct:
                return "matched_fx", details

    # 4) Amount-only fallback (same currency)
    if amt_todo is not None and abs(rem - amt_todo) <= amount_tolerance and currencies_compatible(todo_cur_raw, doc_cur):
        return "matched_amount", details

    return "none", details


def _reason_rank(reason: str) -> int:
    order = {
        "matched_vs_amount": 0,
        "matched_vs": 1,
        "matched_date_amount": 2,
        "matched_fx": 3,
        "matched_amount": 4,
        "none": 99,
    }
    return order.get(reason, 99)


def propose_payment_for_expense(
    expense: Dict[str, Any],
    todos: List[Dict[str, Any]],
    *,
    amount_tolerance: Decimal,
    date_window_days: int,
    fx_client: CnbRatesClient,
    fx_tolerance_czk: Decimal,
    fx_tolerance_pct: Decimal,
) -> Dict[str, Any]:
    """
    Returns a proposal dict with:
      status: matched | ambiguous | no_match
      reason: matched_* | none
      expense: expense payload
      todo: todo payload (when status == matched)
      candidates: optional list for ambiguous
    """
    best: Optional[Tuple[str, Dict[str, Any], Dict[str, Any]]] = None  # (reason, details, todo)
    best_ties: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []

    for todo in todos:
        reason, details = score_todo_for_doc(
            todo,
            expense,
            amount_tolerance=amount_tolerance,
            date_window_days=date_window_days,
            fx_client=fx_client,
            fx_tolerance_czk=fx_tolerance_czk,
            fx_tolerance_pct=fx_tolerance_pct,
        )
        if reason == "none":
            continue

        triple = (reason, details, todo)
        if best is None:
            best = triple
            best_ties = [triple]
            continue

        cur_rank = _reason_rank(reason)
        best_rank = _reason_rank(best[0])
        if cur_rank < best_rank:
            best = triple
            best_ties = [triple]
        elif cur_rank == best_rank:
            # Prefer smaller FX diff when matched_fx
            if reason == "matched_fx":
                diff_new = Decimal(str(details.get("fx_diff_czk") or "999999"))
                diff_best = Decimal(str(best[1].get("fx_diff_czk") or "999999"))
                if diff_new < diff_best:
                    best = triple
                    best_ties = [triple]
                elif diff_new == diff_best:
                    best_ties.append(triple)
            else:
                best_ties.append(triple)

    exp_payload = {
        "expense_id": expense.get("id"),
        "expense_number": expense.get("number") or expense.get("original_number") or expense.get("custom_id"),
        "supplier_name": expense.get("supplier_name") or "",
        "expense_currency": _doc_currency(expense),
        "expense_total": str(expense.get("total") or ""),
        "expense_native_total": str(expense.get("native_total") or ""),
        "expense_remaining": str(_remaining_due(expense)),
        "issued_on": expense.get("issued_on"),
        "due_on": expense.get("due_on"),
        "variable_symbol": expense.get("variable_symbol"),
    }

    if best is None:
        return {"status": "no_match", "reason": "none", "expense": exp_payload}

    if len(best_ties) > 1:
        cands = []
        for reason, details, _todo in best_ties[:5]:
            cands.append({"reason": reason, **details})
        return {
            "status": "ambiguous",
            "reason": best[0],
            "expense": exp_payload,
            "candidates": cands,
        }

    reason, details, todo = best
    params = todo.get("params") or {}
    todo_date = extract_payment_date(todo)
    todo_payload = {
        "todo_id": todo.get("id"),
        "todo_name": todo.get("name"),
        "todo_currency": (params.get("currency") or "").strip().upper() or "CZK",
        "todo_amount": params.get("amount"),
        # Store in a local variable so type checkers can narrow Optional[date].
        "todo_date": todo_date.isoformat() if todo_date else None,
        "todo_vs": params.get("variable_symbol"),
        "bank_account_id": params.get("bank_account_id"),
    }
    return {
        "status": "matched",
        "reason": reason,
        "expense": exp_payload,
        "todo": todo_payload,
        "details": details,
    }


def print_markdown_table(rows: List[Dict[str, Any]]) -> None:
    def short_supplier(name: str) -> str:
        parts = [p for p in str(name or "").strip().split() if p]
        if len(parts) <= 2:
            return " ".join(parts)
        return " ".join(parts[:2])

    def fmt_2(raw: Any) -> str:
        if raw in (None, ""):
            return ""
        try:
            return f"{Decimal(str(raw)):.2f}"
        except Exception:
            return str(raw)

    # Terminal view: compact columns only
    cols = ["expense_number", "supplier_name", "reason", "todo_amount", "fx_diff_czk", "fx_diff_pct"]

    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    print(header)
    print(sep)
    for r in rows:
        exp = r.get("expense") or {}
        todo = r.get("todo") or {}
        det = r.get("details") or {}
        def g(k: str) -> str:
            if k == "supplier_name":
                return short_supplier(exp.get("supplier_name") or "")
            if k in ("fx_diff_czk", "fx_diff_pct"):
                return fmt_2(det.get(k))
            if k == "todo_amount":
                v = todo.get("todo_amount")
                return "" if v in (None, "") else str(v)
            if k == "reason":
                v = r.get("reason")
                return "" if v in (None, "") else str(v)
            if k == "expense_number":
                v = exp.get("expense_number")
                return "" if v in (None, "") else str(v)
            v = exp.get(k) or todo.get(k) or r.get(k) or det.get(k)
            return "" if v in (None, "") else str(v)

        line = "| " + " | ".join(g(c) for c in cols) + " |"
        print(line)


def write_csv(rows: List[Dict[str, Any]], path: str) -> None:
    def fmt_2(raw: Any) -> str:
        if raw in (None, ""):
            return ""
        try:
            return f"{Decimal(str(raw)):.2f}"
        except Exception:
            return str(raw)

    # CSV structure as requested (exact order)
    cols = [
        "expense_number",
        "supplier_name",
        "expense_remaining",
        "expense_currency",
        "reason",
        "todo_amount",
        "todo_currency",
        "todo_date",
        "todo_vs",
        "fx_diff_czk",
        "fx_diff_pct",
    ]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            exp = r.get("expense") or {}
            todo = r.get("todo") or {}
            det = r.get("details") or {}
            out = {c: "" for c in cols}

            out["expense_number"] = exp.get("expense_number") or ""
            out["supplier_name"] = exp.get("supplier_name") or ""
            out["expense_remaining"] = exp.get("expense_remaining") or ""
            out["expense_currency"] = exp.get("expense_currency") or ""
            out["reason"] = r.get("reason") or ""

            out["todo_amount"] = todo.get("todo_amount") or ""
            out["todo_currency"] = todo.get("todo_currency") or ""
            out["todo_date"] = todo.get("todo_date") or ""
            out["todo_vs"] = todo.get("todo_vs") or ""

            out["fx_diff_czk"] = fmt_2(det.get("fx_diff_czk"))
            out["fx_diff_pct"] = fmt_2(det.get("fx_diff_pct"))
            w.writerow(out)


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
    confirm_all: bool,
    interactive: bool,
    output_csv: Optional[str],
) -> int:
    client = FakturoidClient(config)
    logger = setup_pairing_logger()
    if not client.test_connection():
        print("❌ Fakturoid connection failed. Check .env credentials.")
        logger.error("Fakturoid connection failed")
        return 1

    todos = client.list_todos(since=since)
    uncompleted = [t for t in todos if not t.get("completed_at")]
    names = Counter((t.get("name") or "").strip() for t in uncompleted)
    unpaired_expense_todos = [t for t in uncompleted if (t.get("name") or "").strip() == TODO_EXPENSE_UNPAIRED]

    expenses = client.list_unpaid_expenses()
    unpaid_expenses = filter_candidate_docs(expenses, "", enforce_currency=False)

    print(f"Todo filter: since={since or 'all (no date limit)'}")
    print("Uncompleted todos by name:")
    for name, cnt in sorted(names.items(), key=lambda x: (-x[1], x[0])):
        if not name:
            continue
        print(f"  - {name}: {cnt}")

    print()
    print(f"Found {len(unpaired_expense_todos)} unpaired expense payment todo(s).")
    print(f"Found {len(unpaid_expenses)} unpaid expense(s) with remaining balance.\n")

    if not unpaired_expense_todos and since is not None:
        all_uncompleted = [
            t
            for t in client.list_todos(since=None)
            if not t.get("completed_at")
            and (t.get("name") or "").strip() == TODO_EXPENSE_UNPAIRED
        ]
        if all_uncompleted:
            print(
                f"⚠️  V zadaném období (since={since}) není žádný todo, "
                f"ale v celé historii je {len(all_uncompleted)}× {TODO_EXPENSE_UNPAIRED}."
            )
            print(
                "   Zkuste širší období, např.:"
            )
            print("   uv run python pair_payments.py")
            print("   uv run python pair_payments.py --since 1.1.2026\n")
            logger.warning(
                "0 todos in since=%s but %s in full history",
                since,
                len(all_uncompleted),
            )

    logger.info(
        "Loaded todos=%s unpaid_expenses=%s since=%s",
        len(unpaired_expense_todos),
        len(unpaid_expenses),
        since,
    )

    fx = CnbRatesClient()

    proposals: List[Dict[str, Any]] = []
    for exp in sorted(unpaid_expenses, key=lambda x: x.get("issued_on") or ""):
        proposals.append(
            propose_payment_for_expense(
                exp,
                unpaired_expense_todos,
                amount_tolerance=amount_tolerance,
                date_window_days=date_window_days,
                fx_client=fx,
                fx_tolerance_czk=fx_tolerance_czk,
                fx_tolerance_pct=fx_tolerance_pct,
            )
        )

    print("### Proposed pairings (unpaid expenses)")
    print_markdown_table(proposals)

    if output_csv:
        write_csv(proposals, output_csv)
        print(f"\nCSV written to: {output_csv}")
        # Print a clickable path hint for Cursor/terminals that support it.
        print(f"Open: @{output_csv}")
        logger.info("CSV written to %s", output_csv)

    if not execute:
        matched_cnt = sum(1 for p in proposals if p.get("status") == "matched")
        amb_cnt = sum(1 for p in proposals if p.get("status") == "ambiguous")
        no_cnt = sum(1 for p in proposals if p.get("status") == "no_match")
        print()
        print(f"Dry-run finished. matched={matched_cnt}, ambiguous={amb_cnt}, no_match={no_cnt}.")
        if matched_cnt == 0 and no_cnt > 0 and not unpaired_expense_todos:
            print(
                "Žádné párování — chybí nespárované bankovní todos (expense_payment_unpaired). "
                "Výchozí běh načítá všechny todos; pokud používáte --since, zkuste starší datum."
            )
        elif matched_cnt > 0:
            print("Run with --execute to apply, plus --confirm-all or --interactive.")
        else:
            print("Run with --execute to apply, plus --confirm-all or --interactive.")
        logger.info("Dry-run summary matched=%s ambiguous=%s no_match=%s", matched_cnt, amb_cnt, no_cnt)
        return 0

    # Execute mode: never apply ambiguous automatically.
    matched = 0
    skipped = 0
    used_todo_ids: set = set()
    used_expense_ids: set = set()

    # Pre-check conflicts: same todo proposed for multiple expenses
    todo_to_expenses: Dict[str, List[str]] = {}
    for p in proposals:
        if p.get("status") != "matched":
            continue
        tid = str((p.get("todo") or {}).get("todo_id"))
        eid = str((p.get("expense") or {}).get("expense_id"))
        todo_to_expenses.setdefault(tid, []).append(eid)

    conflict_todos = {tid for tid, eids in todo_to_expenses.items() if len(eids) > 1}

    def as_int(value: Any, label: str) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning("Invalid int for %s: %r", label, value)
            return None

    def apply_one(p: Dict[str, Any]) -> None:
        nonlocal matched, skipped
        exp = p.get("expense") or {}
        todo = p.get("todo") or {}
        if p.get("status") != "matched":
            skipped += 1
            return
        eid = as_int(exp.get("expense_id"), "expense_id")
        tid = as_int(todo.get("todo_id"), "todo_id")
        if eid is None or tid is None:
            print(f"  ⏭️  SKIP (invalid_ids) expense={exp.get('expense_number')} todo={todo.get('todo_id')}")
            skipped += 1
            return
        if str(tid) in conflict_todos:
            print(f"  ⏭️  SKIP (todo_conflict) expense={exp.get('expense_number')} todo={tid}")
            skipped += 1
            return
        if tid in used_todo_ids or eid in used_expense_ids:
            print(f"  ⏭️  SKIP (already_used) expense={exp.get('expense_number')} todo={tid}")
            skipped += 1
            return

        # Find full todo object for payload (needs params)
        full_todo = next((t for t in unpaired_expense_todos if as_int(t.get("id"), "todo.id") == tid), None)
        if not full_todo:
            print(f"  ⏭️  SKIP (todo_missing) expense={exp.get('expense_number')} todo={tid}")
            skipped += 1
            return

        # Find full expense
        full_exp = next((e for e in unpaid_expenses if as_int(e.get("id"), "expense.id") == eid), None)
        if not full_exp:
            print(f"  ⏭️  SKIP (expense_missing) expense={exp.get('expense_number')} todo={tid}")
            skipped += 1
            return

        pay_d = extract_payment_date(full_todo)
        effective_paid_on = paid_on or (pay_d.isoformat() if pay_d else date.today().isoformat())
        payload = build_payment_payload(full_todo, full_exp, effective_paid_on)

        try:
            client.create_expense_payment(eid, payload)
            if complete_todos:
                client.toggle_todo_completion(tid)
            used_todo_ids.add(tid)
            used_expense_ids.add(eid)
            matched += 1
            print(f"  ✅ Applied: expense={exp.get('expense_number')} todo={tid} reason={p.get('reason')}")
            logger.info(
                "Applied expense=%s expense_id=%s todo_id=%s reason=%s payload=%s",
                exp.get("expense_number"),
                eid,
                tid,
                p.get("reason"),
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception as ex:
            print(f"  ❌ Error: expense={exp.get('expense_number')} todo={tid} err={ex}")
            logger.exception("Error applying expense=%s todo=%s", exp.get("expense_number"), tid)
            skipped += 1

    if interactive:
        print("\nInteractive mode: y=Yes(apply), n=No(skip), c=Cancel, d=details")
        for p in proposals:
            exp = p.get("expense") or {}
            if p.get("status") != "matched":
                continue
            todo = p.get("todo") or {}
            prompt = (
                f"Apply expense {exp.get('expense_number')} ({exp.get('expense_remaining')} {exp.get('expense_currency')}) "
                f"<= todo #{todo.get('todo_id')} ({todo.get('todo_amount')} {todo.get('todo_currency')}) "
                f"[{p.get('reason')}]? "
            )
            while True:
                ans = input(prompt).strip().lower()
                if ans in ("y", "yes"):
                    apply_one(p)
                    break
                if ans in ("n", "no", "s", "skip", ""):
                    skipped += 1
                    break
                if ans in ("d", "detail", "details"):
                    print(json.dumps(p, ensure_ascii=False, indent=2))
                    continue
                if ans in ("c", "cancel", "q", "quit"):
                    print("Cancelled.")
                    return 0
                print("Please enter y/n/c/d")
    else:
        if not confirm_all:
            print("\nRefusing to execute without --confirm-all or --interactive.")
            return 2
        for p in proposals:
            if p.get("status") == "matched":
                apply_one(p)
            else:
                skipped += 1

    print()
    print(f"Done. Payments created: {matched}, skipped/errors: {skipped}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pair Fakturoid unpaired expense payment todos with unpaid expenses.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute mode (requires --confirm-all or --interactive). If omitted, script runs in guided mode.",
    )
    parser.add_argument(
        "--confirm-all",
        action="store_true",
        help="In execute mode, apply all unambiguous matches at once.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="In execute mode, confirm matches one-by-one in the terminal.",
    )
    parser.add_argument(
        "--output-csv",
        nargs="?",
        const="logs/pairing_report.csv",
        default="logs/pairing_report.csv",
        help="Path to write CSV report (default: logs/pairing_report.csv). If used without a value, uses the default path.",
    )
    parser.add_argument(
        "--no-output-csv",
        action="store_true",
        help="Do not write CSV report file.",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        metavar="DATE",
        help=(
            "Jen todos od tohoto data (Fakturoid since=...). "
            "Formát: 1.1.2026, 01.01.2026, 2026-01-01. "
            "Bez --since se načtou všechny todos (výchozí)."
        ),
    )
    parser.add_argument(
        "--since-all",
        action="store_true",
        help="Stejné jako výchozí (všechny todos); ponecháno pro zpětnou kompatibilitu.",
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
        help="Max day distance between payment date and expense issued_on/due_on, default 3",
    )
    parser.add_argument(
        "--fx-tolerance-czk",
        type=str,
        default="60",
        help="FX match tolerance in CZK (after conversion), default 60",
    )
    parser.add_argument(
        "--fx-tolerance-pct",
        type=str,
        default="5.0",
        help="FX match tolerance in percent (after conversion), default 5.0",
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
        print("ℹ️  DRY-RUN / GUIDED: no payments will be created unless you confirm.\n")

    output_csv = None if args.no_output_csv else args.output_csv

    # Default: all todos (since=None). Optional --since limits the window.
    since: Optional[str] = None
    if args.since:
        try:
            since = parse_since_argument(args.since)
        except ValueError as ex:
            print(f"❌ {ex}")
            return 1
    elif args.since_all:
        since = None

    # Guided mode: run report, then ask user how to proceed.
    if not args.execute and not args.confirm_all and not args.interactive:
        rc = run(
            execute=False,
            amount_tolerance=tol,
            paid_on=args.paid_on,
            complete_todos=not args.no_complete_todo,
            since=since,
            date_window_days=args.date_window_days,
            fx_tolerance_czk=fx_tol_czk,
            fx_tolerance_pct=fx_tol_pct,
            confirm_all=False,
            interactive=False,
            output_csv=output_csv,
        )
        if rc != 0:
            return rc

        try:
            ans = input("\nApply ALL proposed matches now? (y/N): ").strip().lower()
        except EOFError:
            # Non-interactive run (e.g. redirected stdin): behave like "no".
            print("\n(no stdin) OK, nothing applied.")
            return 0
        if ans in ("y", "yes"):
            return run(
                execute=True,
                amount_tolerance=tol,
                paid_on=args.paid_on,
                complete_todos=not args.no_complete_todo,
                since=since,
                date_window_days=args.date_window_days,
                fx_tolerance_czk=fx_tol_czk,
                fx_tolerance_pct=fx_tol_pct,
                confirm_all=True,
                interactive=False,
                output_csv=output_csv,
            )

        try:
            ans2 = input("Apply one-by-one? (y/N): ").strip().lower()
        except EOFError:
            print("\n(no stdin) OK, nothing applied.")
            return 0
        if ans2 in ("y", "yes"):
            return run(
                execute=True,
                amount_tolerance=tol,
                paid_on=args.paid_on,
                complete_todos=not args.no_complete_todo,
                since=since,
                date_window_days=args.date_window_days,
                fx_tolerance_czk=fx_tol_czk,
                fx_tolerance_pct=fx_tol_pct,
                confirm_all=False,
                interactive=True,
                output_csv=output_csv,
            )
        print("OK, nothing applied.")
        return 0

    return run(
        execute=args.execute,
        amount_tolerance=tol,
        paid_on=args.paid_on,
        complete_todos=not args.no_complete_todo,
        since=since,
        date_window_days=args.date_window_days,
        fx_tolerance_czk=fx_tol_czk,
        fx_tolerance_pct=fx_tol_pct,
        confirm_all=args.confirm_all,
        interactive=args.interactive,
        output_csv=output_csv,
    )


if __name__ == "__main__":
    sys.exit(main())
