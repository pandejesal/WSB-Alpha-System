import pathlib, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '.')
from evolve_real import load_csv, max_dd, cagr, first_trading_day_of_month, _tiered_cost_bps, stationary_bootstrap_p
from src.backtest.metrics import safe_sharpe
from src.backtest.gatespec38_tracks import check_track, recompute_dsr, required_sharpe_for_dsr
from src.backtest.walk_forward_engine import WalkForwardValidator
panel = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","JNJ","WMT","MA","PG","UNH","XOM","HD","DIS","BAC","CVX","KO","PEP","COST","AVGO","LLY","ABBV","NKE","CRM","ORCL","NFLX","AMD"]
uni = {t: load_csv(t)['close'] for t in panel}
prices = pd.DataFrame(uni).dropna()
spy = load_csv('SPY')['close'].reindex(prices.index)

def monthly_rotation_ff(prices_df, lookback, skip, top_n, lowvol=False, quality_filter=False):
    rets_local = prices_df.pct_change()
    months = first_trading_day_of_month(prices_df.index)
    w = pd.DataFrame(0.0, index=prices_df.index, columns=prices_df.columns)
    for m in months:
        hist = rets_local.loc[:m].iloc[-(lookback+skip):-skip] if skip else rets_local.loc[:m].iloc[-lookback:]
        if len(hist) < 20:
            continue
        universe_cols = prices_df.columns.tolist()
        if quality_filter:
            vol20 = hist.tail(20).std()
            thresh = vol20.quantile(0.9)
            universe_cols = [c for c in universe_cols if vol20.get(c, 0) <= thresh]
            if len(universe_cols) < top_n:
                universe_cols = prices_df.columns.tolist()
            hist = hist[universe_cols]
        if lowvol:
            score = hist.std().sort_values()
        else:
            mom = hist.mean()
            price_at_m = prices_df.loc[:m].tail(200)
            sma200 = price_at_m.mean()
            last_price = prices_df.loc[m] if m in prices_df.index else prices_df.loc[:m].iloc[-1]
            val = 1.0 / (last_price / sma200.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
            val = val.reindex(hist.columns).fillna(val.median())
            qua = -hist.std()
            def z(s):
                mu=s.mean(); sd=s.std(ddof=1)
                if sd<1e-9: return pd.Series(0, index=s.index)
                return (s-mu)/sd
            composite = (z(mom) + z(val) + z(qua))/3
            score = composite.sort_values(ascending=False)
        picks = list(score.head(int(top_n)).index)
        w.loc[m, picks] = 1.0/len(picks)
    w = w.shift(1).fillna(0.0)
    mask_zero = w.abs().sum(axis=1) < 1e-9
    w[mask_zero] = np.nan
    w = w.ffill().fillna(0.0)
    port = (w * rets_local).sum(axis=1)
    return port, w

def evaluate(port, w, family):
    turnover = w.diff().abs().sum(axis=1)
    turnover.iloc[0]=w.iloc[0].abs().sum()
    cost = _tiered_cost_bps(spy, family).reindex(port.index).fillna(5)/10000
    port_net = port - turnover*cost
    spy_r = spy.pct_change().fillna(0).reindex(port.index).fillna(0)
    excess = float((1+port_net).prod() - (1+spy_r).prod())*100
    sharpe = safe_sharpe(port_net)
    oos = safe_sharpe(port_net.iloc[int(len(port_net)*0.7):])
    tmin = (w.abs().sum(axis=1)>1e-9).mean()
    dd = max_dd((1+port_net).cumprod())
    trips = int((w.diff().abs().sum(axis=1)>1e-9).sum())
    dsr_30 = recompute_dsr(1910, sharpe, 30)
    dsr_100 = recompute_dsr(1910, sharpe, 100)
    dsr_200 = recompute_dsr(1910, sharpe, 200)
    wv = w.reindex(port.index).fillna(0).values
    vals = prices.pct_change().reindex(port.index).fillna(0).values
    actual = sharpe
    rng=np.random.default_rng(7)
    wins=0
    K=200
    perm_cost = _tiered_cost_bps(spy, family).reindex(port.index).fillna(5).values/10000
    for _ in range(K):
        shift=int(rng.integers(1,len(port)))
        ps=np.roll(wv, shift, axis=0)
        tn = pd.Series((ps * vals).sum(axis=1), index=port.index)
        tn = tn - pd.Series(np.abs(np.diff(ps, axis=0, prepend=ps[:1])).sum(axis=1), index=port.index)*pd.Series(perm_cost, index=port.index)
        if safe_sharpe(tn) >= actual:
            wins+=1
    perm_p = wins/K
    boot_p = stationary_bootstrap_p(np.asarray(port_net.values, dtype=float))
    df = pd.DataFrame({'ret': port_net})
    wf = WalkForwardValidator(train_window_days=252, test_window_days=63)
    wf_res = wf.validate(df, lambda d: safe_sharpe(d['ret']) if 'ret' in d else 0.0)
    metrics = {
        'sharpe': sharpe,
        'cagr': cagr((1+port_net).cumprod()),
        'max_dd': dd,
        'oos': oos,
        'trips': trips,
        'trades': trips*2,
        'excess': round(excess,2),
        'tmin': round(float(tmin),4),
        'n_bars': len(port_net),
        'dsr': round(dsr_30,4),
        'dsr_100': round(dsr_100,4),
        'dsr_200': round(dsr_200,4),
        'perm_p': round(perm_p,4),
        'boot_p': round(boot_p,4),
        'wf_status': wf_res.get('status'),
        'wf_reason': wf_res.get('reason',''),
        'check_tracks': check_track({'sharpe':sharpe,'max_dd':dd,'oos':oos,'excess':excess,'dsr':dsr_30,'tmin':tmin,'trips':trips,'perm_p':perm_p,'boot_p':boot_p}),
        'required_sharpe_DSR95_N30': required_sharpe_for_dsr(1910,30,0.95),
        'required_sharpe_DSR92_N30': required_sharpe_for_dsr(1910,30,0.92),
    }
    return metrics, port_net, wf_res

port_fm, w_fm = monthly_rotation_ff(prices, lookback=126, skip=21, top_n=3, lowvol=False, quality_filter=True)
metrics_fm, _, wf_fm = evaluate(port_fm, w_fm, 'factor_momentum')
port_q, w_q = monthly_rotation_ff(prices, lookback=20, skip=0, top_n=10, lowvol=True, quality_filter=True)
metrics_q, _, wf_q = evaluate(port_q, w_q, 'quality_low_vol')
print('FACTOR_MOMENTUM_TOP3 W11 REHAB:')
print(json.dumps(metrics_fm, indent=2))
print('\nQUALITY_LOWVOL_TOP10 W11 REHAB:')
print(json.dumps(metrics_q, indent=2))
pathlib.Path('docs/data').mkdir(parents=True, exist_ok=True)
pathlib.Path('hunts/factor_rotation/test_run/results').mkdir(parents=True, exist_ok=True)
with open('docs/data/cycle15_eval_factor_momentum.json','w') as f: json.dump({'family':'factor_momentum','id':'factor_momentum_top3','w11_rehab':True,'metrics':metrics_fm,'wf':wf_fm,'spy_baseline_same_window':True,'cost_model':'tiered W5','panel':'30-stock'}, f, indent=2)
with open('docs/data/cycle16_eval_quality_low_vol.json','w') as f: json.dump({'family':'quality_low_vol','id':'quality_lowvol_top10','w11_rehab':True,'metrics':metrics_q,'wf':wf_q,'spy_baseline_same_window':True,'cost_model':'tiered W5','panel':'30-stock'}, f, indent=2)
with open('hunts/factor_rotation/test_run/results/factor_momentum_top3_eval.json','w') as f: json.dump(metrics_fm, f, indent=2)
with open('hunts/factor_rotation/test_run/results/quality_lowvol_top10_eval.json','w') as f: json.dump(metrics_q, f, indent=2)
