from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple

import requests


class CnbRatesError(RuntimeError):
    pass


@dataclass(frozen=True)
class CnbRate:
    """CZK per `amount` units of `code` for a given fixing date."""

    fixing_date: date
    code: str
    amount: int
    czk: Decimal

    def czk_per_1(self) -> Decimal:
        if self.amount <= 0:
            raise ValueError("Invalid CNB rate amount")
        return self.czk / Decimal(self.amount)


class CnbRatesClient:
    """
    Minimal CNB rates client (daily fixing).

    Source TXT format:
      https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt?date=DD.MM.RRRR
    """

    def __init__(self, timeout_s: int = 10):
        self.timeout_s = timeout_s
        # Cache: requested date_str -> (fixing_date_str, rates_by_code)
        self._cache: Dict[str, Tuple[str, Dict[str, CnbRate]]] = {}

    @staticmethod
    def _to_date(d: date | str) -> date:
        if isinstance(d, date):
            return d
        s = str(d).strip()
        # Accept ISO or CNB format.
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unsupported date format: {d!r}")

    @staticmethod
    def _fmt_cnb_query_date(d: date) -> str:
        return d.strftime("%d.%m.%Y")

    @staticmethod
    def _parse_first_line_date(line: str) -> date:
        # Examples:
        # - "17.04.2026 #74"
        # - "24 Apr 2026 #79"
        raw = line.strip().split("#", 1)[0].strip()
        for fmt in ("%d.%m.%Y", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        raise CnbRatesError(f"Unable to parse CNB fixing date from: {line!r}")

    @staticmethod
    def _parse_txt(body: str) -> Tuple[date, Dict[str, CnbRate]]:
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        if len(lines) < 3:
            raise CnbRatesError("Unexpected CNB TXT format (too few lines)")

        fixing_date = CnbRatesClient._parse_first_line_date(lines[0])
        # lines[1] is header
        rates: Dict[str, CnbRate] = {"CZK": CnbRate(fixing_date=fixing_date, code="CZK", amount=1, czk=Decimal("1"))}
        for ln in lines[2:]:
            parts = ln.split("|")
            if len(parts) != 5:
                continue
            _country, _currency_name, amount_s, code, rate_s = parts
            code = code.strip().upper()
            try:
                amount = int(amount_s.strip())
            except ValueError:
                continue
            # CZ format uses comma; EN uses dot.
            rate = Decimal(rate_s.strip().replace(",", "."))
            rates[code] = CnbRate(fixing_date=fixing_date, code=code, amount=amount, czk=rate)

        return fixing_date, rates

    def _fetch_txt(self, d: date) -> str:
        url = (
            "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/"
            "kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt"
        )
        params = {"date": self._fmt_cnb_query_date(d)}
        resp = requests.get(url, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.text

    def get_rate_czk_per_1(self, currency: str, for_date: date | str) -> Optional[Decimal]:
        """
        Returns CZK per 1 unit of `currency` as Decimal, or None when the currency
        isn't present in the CNB fixing.
        """
        cur = (currency or "").strip().upper()
        if cur == "":
            return None
        if cur == "CZK":
            return Decimal("1")

        d = self._to_date(for_date)
        key = d.isoformat()
        if key not in self._cache:
            fixing_date, rates = self._parse_txt(self._fetch_txt(d))
            self._cache[key] = (fixing_date.isoformat(), rates)

        _fixing_date_str, rates = self._cache[key]
        r = rates.get(cur)
        if not r:
            return None
        return r.czk_per_1()

