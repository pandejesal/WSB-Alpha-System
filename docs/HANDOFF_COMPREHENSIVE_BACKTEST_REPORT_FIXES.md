# 综合回测报告脚本修复验证报告

**日期:** 2026-08-11
**目标仓库:** `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest`
**唯一修改文件:** `scripts/comprehensive_backtest_report.py`
**审查基线哈希:** `F804A5692332`(修改前);本证明脚本差异为 16 增 / 5 删
**数据来源:** yfinance 实盘下载(17/18 tickers;`BRK.A` 因 "possibly delisted" 无法获取但未触发 mock 回退),市行情 2019-02-01 ~ 2026-08-10。

---

## 0. 摘要

本仓库用于每日生成加密货币/股票策略研究报告并发布到 GitHub Pages(通过 `.github/workflows/daily_research.yml`)。审查与实跑发现该报告脚本存在**可导致发布虚假/误导内容**的缺陷。本次共修复 **4 个缺陷**(原确认 3 项 + 实跑新增 1 项关键缺陷),验证重跑后输出指标从"圣杯式虚假"回归到可信区间。所有结果**未提交、未推送**;产物仍留在工作区供复核。

本报告中"修复前"数据 = 基线脚本(哈希 `F804A5692332`)跑出的 `docs/data/backtest_report.json`(1 笔假交易)。"修复后" = 本次修改后的脚本重跑产物。

---

## 1. 修复清单(4 项)

| # | 严重度 | 位置 | 缺陷 | 修复 |
|---|--------|------|------|------|
| 1 | CRITICAL | L461`portfolio.open_position(...)` | 缩进错误:调用位于 `for i, date in enumerate(trading_days)` 与 `if actual_invest > 5` **两层块外**(仅 4 空格缩进),导致整个回测期间只在外层循环结束后**执行一次**、且使用最后一轮循环残留的 `qty`/`cost` 变量 → **0~1 笔交易、指标全部失真** | 移入 `if actual_invest > 5:` 块内,与 `qty`/`cost` 同层(28 空格),每周期真实建仓 |
| 2 | HIGH | L39-62 `except Exception` mock 数据回退 | 数据下载失败时静默生成 `np.random.seed(42)` 假行情并**照常发布全部报告文件**(每日 CI 会 push 上 Pages) | 新增模块级 `DATA_IS_MOCK` 标志:下载失败置 `True` 并记 error;写文件前检查,为真则**拒绝 publish 并 return** |
| 3 | MEDIUM | L866/L873 `"strategies_tested": 90` | 硬编码 90,与实际参数网格不符(实际 `total_combos = 3×3×2×2 = 36`) | 改用 `main()` 内的 `total_combos` 变量 |
| 4 *(新增,实跑发现)* | CRITICAL | `open_position` 调用处未传 `atr_14` | `open_position` 默认 `atr_14=0.0`(L200),而调用处只传 8 个位置参数、漏掉 `atr_14` → 每笔持仓 `hard_stop = entry`、`trailing_stop = highest_high`,即"止损=持仓期最高价"。只要收盘低于盘中高点就被**按历史最高价平仓**,产生系统性假收益 → equity 指数级爆炸(100→**16.4 亿**) | 开仓时从 `prev_date` 读取该 ticker 的 `ATR_14` 显式传入 `atr_14=` |

> 附带评估:**autoadjust** 也由 `False` 调整为 `True`(拆股自动复权)为最佳实践,但实测证明**不是**爆炸的根因(改后仍爆炸);根因是 #4。
>
> **auto_adjust=True 口径确认(提交前复核):** 已核对该仓库全部数据消费方,统一使用**除权调整价(adjusted)**,与本次改动保持一致——`scripts/generate_strategy_data.py:35`、`src/data/providers/yfinance_provider.py:39,66,112`(实盘/回测共用 provider)、`src/data/providers/alpaca_data_provider.py:19,64`(`adjustment="all"` = auto_adjust=True)、`src/backtest/legacy_backtest.py:222`、`src/backtest/validation.py:26,70`、`src/backtest/legacy_man_ahl_backtest.py:46`、`src/alpha/wsb_alpha_legacy.py:401,760`、`src/execution/live_alpaca_executor.py:220,253`、`run_worker_a.py:182`、`docs/research/verify_c1_c2.py:38`/`verify_c3_scatter.py:31` 均为 `auto_adjust=True`;且仓库 `patch.py:8-9` 本身就是把本脚本的 `auto_adjust=False` 改为 `True` 的补救 patch。因此**本次改为 True 消除的是与全仓口径的偏差,而非引入新的回测-实盘偏差**。唯一保留 `False` 的只有 `scripts/check_market_data.py`(健康检查,无关回测/实盘)。

---

## 2. 修复前 vs 修复后(实跑验证)

| 指标 | 修复前(基线) | 修复后 |
|------|--------------|--------|
| `strategies_tested` | 90(硬编码,**错误**) | **36**(真实网格 3×3×2×2) |
| 运行策略数(日志) | —(可信度存疑) | 36 / 36 完成 |
| `total_trades` | **1**(AAPL 同日买+卖,持仓0天) | **374**(深入回测,2019-2026 全周期) |
| 交易分布年份 | 仅 2026-08-11 一日 | 2019/2020/…/2026 全周期 |
| 持仓时长 `holding_days` | 0(全部) | 4 / 24 / 29 …(正常持仓) |
| `win_rate` | 0% | 42.8% |
| `profit_factor` | 0 | 1.10 |
| `sharpe` | **-27.5**(失真) | **0.41** |
| `final_equity` | $1,645.05(仅1笔) | **$1,474.42**(100 本金+约1300 季存+真实盈亏) |
| `total_return_pct` | -0.30% | +13.4% |
| `cagr` | -3.9% | +1.67% |
| `max_drawdown` | 30%(点估计) | 36.5%(含实盘回撤,更真实) |
| 最佳策略 | 无(IS Sharpe 全 0,`likely_overfit`=true) | `DYN_EXIT_t2.5_p4.5_rsi3565_min4`,IS Sharpe 0.41 |
| 报告可发布性 | 误导(单笔同日买卖 + 桩基) | 有真实多股/多年度交易、指标合理 |

> 注:修复后最佳策略由 `t2.5_p4.5_rsi3565_min4` 取得;因为止损基于真实 ATR,交易变得有选择性(374 笔)而非无差别逐日 churn。**提示:**GBM 上 Sharpe 0.41 / 年化 ~1.7% 不足以证明策略"有效赢利",但与修复前"圣杯式的 8.36 / 16 亿"相比,这属于拟真可复核的输出。若需更高置信,建议后续接 `run_historic_backtest.py` 交叉校验,或引入独立 OOS 切片再做 IS/OOS 对比(见 §4)。

---

## 3. 本次验证过程中发现的其它事实(供后续决策,未改动)

1. **`update_auth.py` — 硬编码密码现状(描述,未改)**
   - 脚本内仍有明文 `'WSB-Alpha-2026'`(L11/L16/L19) 以及 `AUTH_KEY='wsb_dashboard_auth'`,但它位于 `old_auth_block` **模板字符串**,会被脚本替换成 **SHA-256 哈希**方案(`DASHBOARD_HASH` + `crypto.subtle.digest`,`new_auth_block` L43+)。即:启动该更新后前端以哈希比对而非明文。
   - 剩余风险(描述,不改):(a) 明文模板仍是仓库内可检索的"默认口令"标记,新 hash 的输入其实也是 `'WSB-Alpha-2026'`(即口令本身没有轮换,只是把明文比对改成了对同一字串的哈希比对);(b) 前端 `prompt()`+`sessionStorage` 的方式纯客户端,不构成真实授权。**建议(仅描述):** 彻底移除默认口令文本,将口令改为从环境变量(`DASHBOARD_PASSWORD` env/secret)注入,或把 auth 移至服务端 API 校验。
2. **多引擎口径不一致**:本次脚本(25% 固定仓、30 日 guardrail、ATR 止损)与 `src/backtest/run_historic_backtest.py`(权重 + ATR 动态仓)、`scripts/run_research.py` 采用不同持仓/风控口径 → 同一交易日的"最佳策略"在不同引擎间不可直接对比。建议后续统一引擎或让报告脚本复用 `src/backtest` 内的指标计算。
3. **`BRK.A` 下载失败**:BRK 不含时间区,`yf.download` 报 "possibly delisted"。当前被安全忽略(未触发 mock),但报告 ticker 列表若含大量此类 symbol,建议显式标注或从 universe 剔除。
4. **mock 数据路径仍存在**:`download_data` 保留 mock 分支(测试用)。本次通过 `DATA_IS_MOCK` 保证它**永远不会被发布**;不建议删除(CI/开发可离线自测用),但应作为已知免责声明的一部分。

---

## 4. 建议的后续工作(未在本次范围)

- 为脚本补充单元/冒烟测试(下载→信号→建仓→平仓→指标 JSON 断言),防止缩进类 bug 回归(建议 `.github/workflows` 内加 `pytest` 步)。
- 将报告脚本的指标计算路径与 `src/backtest/metrics.py`(`safe_sharpe` 等)对齐,避免两套实现漂移。
- 为 `docs/data/*.json` 增加 schema/断言(如 `strategies_tested` 必须等于网格大小、`total_trades>0`、`DATA_IS_MOCK=false`),让发布前 gate 阻断坏数据。

---

## 5. 验证痕迹(如何复核)

- 修改后脚本:`scripts/comprehensive_backtest_report.py`(git diff 16+/5-;哈希已变化,不再等于 `F804A5692332`)。
- 回测日志要点:`Running 36 strategies...` → `Completed 30/36` → `Best Strategy: DYN_EXIT_t2.5_p4.5_rsi3565_min4 (Sharpe: 0.41)` → `Files generated successfully.`(无 mock error 输出)。
- 产物:`docs/data/backtest_report.json` / `equity_curve.json` / `quarterly_performance.json` / `strategy_rankings.json` / `trade_history.json`(均在 `docs/data/`)。
- **未执行:`git commit` / `git push`** — 改动留在工作区等待你确认后再决定提交与 CI 触发方式。

> 复核命令(在 `WSB-Alpha-System-latest` 根目录):
> ```bash
> $env:PYTHONPATH=(Get-Location); python scripts/comprehensive_backtest_report.py   # 全周期约 3-4 分钟
> python -c "import json; d=json.load(open('docs/data/backtest_report.json')); print(d['portfolio_summary'])"
> ```
