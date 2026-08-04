import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Update the parameter grid in main
grid_orig = """    # Parameters
    holding_periods = [3, 5, 7, 10, 15]
    rsi_thresholds = [(30, 70), (35, 65), (40, 60)]
    gk_limits = [0.8, 1.0, 1.2]
    min_confluences = [3, 4]

    all_strategies = []

    total_combos = len(holding_periods) * len(rsi_thresholds) * len(gk_limits) * len(min_confluences)
    logger.info(f"Running {total_combos} strategies...")

    best_portfolio = None
    best_sharpe = -999
    best_params = None
    best_metrics = None
    best_overfitting = None

    strat_idx = 0
    for hp in holding_periods:
        for rsi in rsi_thresholds:
            for gk in gk_limits:
                for mc in min_confluences:
                    params = {
                        'holding_days': hp,
                        'rsi_bounds': rsi,
                        'gk_limit': gk,
                        'min_confluence': mc
                    }

                    name = f"HA_MACD_RSI_BB_hp{hp}_rsi{rsi[0]}{rsi[1]}_gk{gk}_min{mc}\""""

grid_new = """    # Parameters
    atr_trailing_mults = [1.5, 2.0, 2.5]
    atr_profit_mults = [2.5, 3.5, 4.5]
    rsi_thresholds = [(30, 70), (35, 65)]
    min_confluences = [3, 4]

    all_strategies = []

    total_combos = len(atr_trailing_mults) * len(atr_profit_mults) * len(rsi_thresholds) * len(min_confluences)
    logger.info(f"Running {total_combos} strategies...")

    best_portfolio = None
    best_sharpe = -999
    best_params = None
    best_metrics = None
    best_overfitting = None
    best_name = None

    strat_idx = 0
    for t_mult in atr_trailing_mults:
        for p_mult in atr_profit_mults:
            for rsi in rsi_thresholds:
                for mc in min_confluences:
                    params = {
                        'atr_trailing_mult': t_mult,
                        'atr_profit_mult': p_mult,
                        'rsi_bounds': rsi,
                        'min_confluence': mc
                    }

                    name = f"DYN_EXIT_t{t_mult}_p{p_mult}_rsi{rsi[0]}{rsi[1]}_min{mc}\""""

content = content.replace(grid_orig, grid_new)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
