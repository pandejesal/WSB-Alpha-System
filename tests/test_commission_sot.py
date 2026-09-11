"""R-C3: commission single source of truth, reference-only (2 tests).

The canonical constant lives in config/risk_config.py; evolve_real and the
harness import it. No numeric value changes (quant reconciliation out of
scope): evolve stays 2.5bp retail, harness default stays 1.0bp.
"""

import inspect


def test_rc3_three_imports_resolve_to_one_canonical():
    from config.risk_config import CANONICAL_COMMISSION_BPS

    import evolve_real
    from src.evolution import agentquant_harness as harness

    assert evolve_real.CANONICAL_COMMISSION_BPS_REF == CANONICAL_COMMISSION_BPS
    assert harness._CANONICAL_COMMISSION_BPS == CANONICAL_COMMISSION_BPS


def test_rc3_operational_values_unchanged():
    from config.risk_config import CANONICAL_COMMISSION_BPS

    import evolve_real
    from src.evolution.agentquant_harness import backtest_strategy

    assert CANONICAL_COMMISSION_BPS == 1.0
    assert evolve_real.COST_COMMISSION_BPS == 2.5
    default = inspect.signature(backtest_strategy).parameters["commission_bps"].default
    assert default == 1.0
