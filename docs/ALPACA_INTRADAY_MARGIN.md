# Alpaca Intraday Margin Rule (replaces PDT) — system impact note

Source: https://docs.alpaca.markets/us/docs/the-intraday-margin-rule (read 2026-09-04).
Upstream: FINRA-mandated, replaces legacy Pattern Day Trader system.

## What changed (facts)

- PDT designation ELIMINATED. No round-trip counting, no 3-day-trades-in-5-days lock.
- $25,000 day-trading minimum REMOVED. Reg-T floor remains (~$2,000 equity
  for margin debits/shorts).
- Unlimited day trades, but regulation is now EXPOSURE-based: dynamic
  buying power, intraday P&L counts toward margin, FDIC sweeps + same-day
  deposits count as equity.
- Intraday Margin Deficit (IMD) → margin call, 2 business days to meet;
  unmet by day 5 → 90-day freeze on new shorts/debits. De minimis: no call
  if deficit < $1,000 or 5% of equity (whichever lower).

## Impact on WSB-Alpha-System: none on code paths

- Zero references to PDT / pattern-day / $25k anywhere in src/, scripts/,
  tests/, strategies/. Verified 2026-09-04 by grep.
- `RiskConfig.max_trades_per_day = 10` (openprophet port) and
  `max_trades_per_day` in alptrading safety are COST-discipline caps, not
  regulatory logic — they stay as-is.
- Paper engine holds no margin and tracks no day-trade count, so the rule
  changes nothing in backtests or the sandbox.

## Live-trading note (for the day we ever go live, currently forbidden)

- Size against real-time IML, not a trade counter; a 5%-equity daily halt
  (already our default) is stricter than the IMD de-minimis band.
- Never let a halt TRAP a position: risk-reducing exits bypass breakers
  (already implemented in alptrading_safety.check_order).

## Implemented mirror (2026-09-04, paper-only)

`src/risk/alptrading_safety.py` now carries the rule mechanics as a
paper model (no broker calls):

- `IntradayMarginState` — start-day equity, exposure, intraday P&L,
  open calls, restriction flag.
- `intraday_buying_power()` — running calculation: (equity + intraday
  P&L) x 4 minus exposure; 1x cash-only below the $2,000 floor
  (was $25,000 under PDT).
- `check_intraday_order()` — Pre-Trade Check: rejects orders that would
  create a deficit (de minimis under min($1,000, 5% equity) passes);
  risk-reducing exits always bypass.
- `record_margin_call()` / `meet_margin_calls()` — 5 unmet daily calls
  restrict new debits (90-day freeze semantics as a flag); meeting
  calls lifts it.
- Tests: `test_intraday_buying_power` in
  tests/test_alptrading_port.py — all green.
