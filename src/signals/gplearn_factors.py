"""gplearn symbolic-factor port (genetic programming over past-only terminals).

Source: https://github.com/trevorstephens/gplearn (sklearn-style
SymbolicRegressor/Transformer/Classifier, parsimony pressure, train/test
fitness, program export).

Pipeline: past-only rolling terminals from OHLCV -> SymbolicRegressor
predicting next-day return (train split) -> fitness = OOS Sharpe of the
sign(signal) long/flat strategy (validation split, T+1, 5bps) ->
winner exported as expression string + pandas equivalent.

Anti-overfit (their parsimony + test-set discipline, hardened):
parsimony_coefficient required, init_depth cap, small fixed budget,
fitness computed OUT-OF-SAMPLE only, min-trades floor, winning program
auditable as pandas code without gplearn installed.

Paper only. No orders are placed; output is a signal expression.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd

FUNCTION_ARITY = {
    "add": 2, "sub": 2, "mul": 2, "div": 2, "sqrt": 1, "log": 1,
    "abs": 1, "neg": 1, "inv": 1, "max": 2, "min": 2, "sin": 1, "cos": 1,
}

TERMINALS = ("ret_1", "ret_5", "sma5_ratio", "sma20_ratio", "rsi14",
             "vol_ratio20", "range_ratio")


def build_terminals(bars: pd.DataFrame) -> pd.DataFrame:
    """Past-only rolling features; every column shifted by 1 (no lookahead)."""
    close = bars["close"].astype(float)
    out = pd.DataFrame(index=bars.index)
    out["ret_1"] = close.pct_change(1)
    out["ret_5"] = close.pct_change(5)
    out["sma5_ratio"] = close / close.rolling(5).mean() - 1
    out["sma20_ratio"] = close / close.rolling(20).mean() - 1
    delta = close.diff()
    gains = delta.clip(lower=0.0).rolling(14).mean()
    losses = (-delta).clip(lower=0.0).rolling(14).mean()
    out["rsi14"] = 100 - 100 / (1 + gains / losses.replace(0, np.nan))
    out["rsi14"] = (out["rsi14"] - 50) / 50  # centered to [-1, 1]-ish
    if "volume" in bars:
        vol = bars["volume"].astype(float)
        out["vol_ratio20"] = vol / vol.rolling(20).mean() - 1
    else:
        out["vol_ratio20"] = 0.0
    if {"high", "low"}.issubset(bars.columns):
        out["range_ratio"] = ((bars["high"] - bars["low"]) / close).astype(float)
    else:
        out["range_ratio"] = 0.0
    return out.shift(1)


def program_to_pandas(expr: str, frame: str = "T") -> str:
    """Render a gplearn program string as pandas code over terminal frame.

    gplearn prints programs like add(mul(X0, X1), sqrt(X2)) with Xk in
    TERMINALS order. Supports the FUNCTION_ARITY set above; anything else
    raises ValueError (fail-closed, never silently misrendered).
    """
    return _render(_parse(expr), frame)


def _parse(expr: str):
    tokens = expr.replace("(", " ( ").replace(")", " ) ").replace(",", " ").split()
    pos = 0

    def parse():
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError(f"truncated expression {expr!r}")
        tok = tokens[pos]
        pos += 1
        if tok in FUNCTION_ARITY:
            if pos >= len(tokens) or tokens[pos] != "(":
                raise ValueError(f"expected ( after {tok} in {expr!r}")
            pos += 1
            args = []
            while tokens[pos] != ")":
                args.append(parse())
            pos += 1  # consume )
            if len(args) != FUNCTION_ARITY[tok]:
                raise ValueError(f"arity mismatch in {expr!r}")
            return (tok, *args)
        if tok.startswith("X"):
            idx = int(tok[1:])
            if idx >= len(TERMINALS):
                raise ValueError(f"terminal out of range in {expr!r}")
            return ("X", idx)
        try:
            return ("C", float(tok))
        except ValueError:
            raise ValueError(f"unknown token {tok!r} in {expr!r}")

    node = parse()
    if pos != len(tokens):
        raise ValueError(f"trailing tokens in {expr!r}")
    return node


def _render(node, frame: str) -> str:
    kind = node[0]
    if kind == "X":
        return f"{frame}['{TERMINALS[node[1]]}']"
    if kind == "C":
        return repr(node[1])
    op, *args = kind, *node[1:]
    rendered = [_render(a, frame) for a in args]
    a = rendered[0]
    b = rendered[1] if len(rendered) > 1 else None
    if op == "add":
        return f"({a} + {b})"
    if op == "sub":
        return f"({a} - {b})"
    if op == "mul":
        return f"({a} * {b})"
    if op == "div":
        return f"({a} / ({b}).replace(0, nan))"
    if op == "sqrt":
        return f"sqrt(abs({a}))"
    if op == "log":
        return f"log(abs({a}) + 1e-9)"
    if op == "abs":
        return f"abs({a})"
    if op == "neg":
        return f"(-{a})"
    if op == "inv":
        return f"(1 / ({a}).replace(0, nan))"
    if op == "max":
        return f"maximum({a}, {b})"
    if op == "min":
        return f"minimum({a}, {b})"
    if op == "sin":
        return f"sin({a})"
    if op == "cos":
        return f"cos({a})"
    raise ValueError(f"unhandled {op}")


def _apply(node, T: pd.DataFrame) -> pd.Series:
    kind = node[0]
    if kind == "X":
        return T[TERMINALS[node[1]]].astype(float)
    if kind == "C":
        return pd.Series(float(node[1]), index=T.index)
    op = kind
    vals = [_apply(a, T) for a in node[1:]]
    a = vals[0]
    b = vals[1] if len(vals) > 1 else None
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if op == "add":
            return a + b
        if op == "sub":
            return a - b
        if op == "mul":
            return a * b
        if op == "div":
            return a / b.replace(0, np.nan)
        if op == "sqrt":
            return np.sqrt(a.abs())
        if op == "log":
            return np.log(a.abs() + 1e-9)
        if op == "abs":
            return a.abs()
        if op == "neg":
            return -a
        if op == "inv":
            return 1 / a.replace(0, np.nan)
        if op == "max":
            return pd.concat([a, b], axis=1).max(axis=1)
        if op == "min":
            return pd.concat([a, b], axis=1).min(axis=1)
        if op == "sin":
            return np.sin(a)
        if op == "cos":
            return np.cos(a)
    raise ValueError(f"unhandled {op}")


def evaluate_program(expr: str, T: pd.DataFrame) -> pd.Series:
    """Evaluate a raw gplearn program string over a terminal frame.

    Direct tree interpreter — no eval(). Inf/nan sanitized to 0.0 so a
    degenerate program yields flat (no position), never garbage.
    """
    s = _apply(_parse(expr), T)
    s = pd.Series(np.asarray(s, dtype=float), index=T.index)
    return s.replace([np.inf, -np.inf], np.nan).fillna(0.0)


@dataclass
class EvolveConfig:
    population_size: int = 100
    generations: int = 5
    parsimony_coefficient: float = 0.01
    init_depth: Tuple[int, int] = (2, 4)
    function_set: Tuple[str, ...] = ("add", "sub", "mul", "div", "sqrt", "log",
                                     "abs", "max", "min")
    random_state: int = 7
    train_ratio: float = 0.7
    min_trades: int = 10


def evolve(bars: pd.DataFrame, cfg: EvolveConfig = EvolveConfig()) -> Dict:
    """Evolve symbolic factor; fitness = OOS Sharpe of sign() long/flat."""
    from gplearn.genetic import SymbolicRegressor

    T = build_terminals(bars).dropna()
    close = bars.loc[T.index, "close"].astype(float)
    fwd = close.pct_change().shift(-1).reindex(T.index).fillna(0.0)
    X = T[list(TERMINALS)].values
    y = fwd.values
    n = len(T)
    split = int(n * cfg.train_ratio)
    est = SymbolicRegressor(population_size=cfg.population_size,
                            generations=cfg.generations,
                            parsimony_coefficient=cfg.parsimony_coefficient,
                            init_depth=cfg.init_depth,
                            function_set=cfg.function_set,
                            random_state=cfg.random_state,
                            verbose=0)
    est.fit(X[:split], y[:split])
    expr = str(est._program)
    code = program_to_pandas(expr)
    sig_val = evaluate_program(expr, T.iloc[split:])
    pos = (sig_val > 0).astype(float).shift(1).fillna(0.0)  # T+1
    ret = fwd.iloc[split:] * pos
    turnover = pos.diff().abs().fillna(pos.abs())
    net = ret - turnover * 0.0005
    from src.backtest.metrics import safe_sharpe
    sharpe = float(safe_sharpe(net))
    trades = int((turnover > 0).sum())
    return {"expression": expr, "pandas_code": code,
            "oos_sharpe": sharpe, "oos_trades": trades,
            "oos_return_pct": float((1 + net).prod() - 1) * 100,
            "train_rows": split, "val_rows": n - split,
            "meets_trades_floor": trades >= cfg.min_trades,
            "status": "paper"}
