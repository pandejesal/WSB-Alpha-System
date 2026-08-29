"""Edge-case tests for minerva_score (paper 2608.23808)."""

import pytest
from src.backtest.defend.minerva_score import minerva_score


def test_t_le_1_raises():
    with pytest.raises(ValueError, match="T must be >1"):
        minerva_score(T=1, sr=1.0, N=10)


def test_n_lt_1_raises():
    with pytest.raises(ValueError, match="N must be >=1"):
        minerva_score(T=100, sr=1.0, N=0)


def test_all_zero_sharpe():
    result = minerva_score(T=100, sr=0.0, N=10)
    assert 0 <= result.display_0_100 <= 100
    assert result.verdict in ("SEAL", "PASS", "FAIL")


def test_none_sharpe_degrades():
    result = minerva_score(T=100, sr=0.0, N=10, pbo=None, spa_p=None, regime_z=None, mtr_pass=None)
    assert 0 <= result.display_0_100 <= 100


def test_extreme_no_overfit_seal_pass():
    result = minerva_score(
        T=2500, sr=2.0, N=100,
        pbo=0.01, spa_p=0.001, regime_z=0.1, mtr_pass=True,
    )
    assert result.seal is True
    assert result.verdict == "SEAL"
    assert result.display_0_100 >= 80


def test_extreme_overfit_seal_fail():
    result = minerva_score(
        T=100, sr=-0.5, N=10,
        pbo=0.9, spa_p=0.5, regime_z=3.0, mtr_pass=False,
    )
    assert result.seal is False
    assert result.verdict == "FAIL"


def test_typical_case():
    result = minerva_score(T=1000, sr=1.2, N=50, pbo=0.2, spa_p=0.03, regime_z=1.1, mtr_pass=True)
    assert 0 <= result.display_0_100 <= 100
    assert result.verdict in ("SEAL", "PASS", "FAIL")
