# Source: https://arxiv.org/list/q-fin.ST/new

**Fetched:** 2026-09-09T15:10:15.611181+00:00

---

Statistical Finance 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 Skip to main content 
 
 
 
 
 

 
 
 

 
 
 
 
 
 
 

 
 
 
 
 
 Search
 
 Submit 
 Donate 
 
 Log in 
 
 

 
 
 
 Search arXiv 
 
 
 
 
 
 Press Enter to search · Advanced search 
 
 
 
 
 
 
 
 Statistical Finance 

 
 New submissions 
 Cross-lists 
 Replacements 
 

 See recent articles 
 Showing new listings for Wednesday, 9 September 2026 

 Total of 7 entries 
 
 Showing up to 2000 entries per page:
 
 fewer 
 |
 more 
 |
 all 

 

 
 New submissions (showing 1 of 1 entries) 

 
 [1] 
 
 arXiv:2609.06422
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Asymmetric Long-Memory GARCH: Sign-Dependent Kernel Injection in a Two-Dimensional Markov Chain
 
 Kennedy Titus Kayaki , Kyungsub Lee 

 Comments: 
 40 pages, 7 figures, 21 tables, Includes supplementary appendix
 

 Subjects: 
 Statistical Finance (q-fin.ST) 
 

 
 We introduce ALM-GARCH, an asymmetric long-memory GARCH model in which positive and negative innovations enter conditional variance with different injection amplitudes and kernel offsets. These departures define testable level and memory channels relative to a nested symmetric benchmark. Positive Harris recurrence holds for interior configurations under a Foster-Lyapunov condition. Across five equity indices and Bitcoin, joint symmetry is rejected throughout, driven primarily by the level channel. The memory channel is supported for the Nikkei 225, KOSPI, and Bitcoin but is weakly identified when the positive branch is nearly inactive. Out-of-sample performance is broadly comparable to standard benchmarks.
 
 
 
 

 
 Cross submissions (showing 5 of 5 entries) 

 
 [2] 
 
 arXiv:2609.06267
 
 (cross-list from stat.AP)

 [ pdf , other ]
 
 
 
 Title: 
 From Discrete Trailing Returns to a Continuous Graphical Profile: Return-to-Present Curves
 
 Lei Liu 

 Subjects: 
 Applications (stat.AP) ; Statistical Finance (q-fin.ST)
 

 
 Investment performance is commonly presented either as a conventional cumulative-return chart, which fixes a historical starting date and traces performance forward, or as a trailing-return table, which fixes the current endpoint but reports only a small set of prespecified horizons. These two displays have complementary limitations: fixed-start comparisons are conditional on the selected origin, whereas trailing returns provide only discrete snapshots of the underlying fixed-endpoint return function. We present the Return-to-Present (RTP) curve as a continuous fixed-endpoint representation that brings these perspectives together by holding the evaluation date fixed while allowing the hypothetical historical purchase date to vary over the available history. Familiar 1-month, 3-month, 6-month, 1-year, and longer trailing returns therefore become selected points on a continuous curve. When multiple investments are overlaid, RTP directly displays entry-date sensitivity, persistent relative advantage, crossings, and the timing and magnitude of separation without requiring selection of a single historical origin. The same endpoint-based construction naturally accommodates investments with unequal inception dates, recurring purchases, and retrospective portfolio rotation decisions in which sale and replacement-purchase dates may differ. We illustrate these uses with real investment data and discuss its relationship to momentum. RTP does not define a new return measure; its contribution is a simple graphical organization of familiar realized returns for historical comparison and decision support rather than prediction or statistical inference.
 
 
 
 
 [3] 
 
 arXiv:2609.07207
 
 (cross-list from econ.EM)

 [ pdf , html , other ]
 
 
 
 Title: 
 Filtering without recursion and some of its uses in financial economics
 
 Simon Donker van Heel , Neil Shephard 

 Subjects: 
 Econometrics (econ.EM) ; Statistical Finance (q-fin.ST); Methodology (stat.ME)
 

 
 We develop a filter for time series, defined at each time $t$ as the minimizer of a discounted convex combination of observed and expected losses. The filter can be estimated by simulation to an arbitrary level of accuracy in $O(1)$ flops at each time point $t$ and can be run for all values $t=1,...,T$ in parallel. These methods are applied to robustly compute a preaveraged price process from the more than 1.5 million trades made on a single financial asset in a single day where the noise's variance is infinite. It yields a flat "volatility signature" plot, down to the 1 second level, so the microstructure noise no longer biases the volatility estimate. This is not true when linear methods are employed.
 
 
 
 
 [4] 
 
 arXiv:2609.07989
 
 (cross-list from q-fin.TR)

 [ pdf , html , other ]
 
 
 
 Title: 
 Regimes in the Order Flow
 
 Ramzi Jebali 

 Comments: 
 59 pages. 48 figures. Summer research project of ENSTA at Scuola Normale Superiore (Pisa)
 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) ; Computational Finance (q-fin.CP); Mathematical Finance (q-fin.MF); Statistical Finance (q-fin.ST)
 

 
 Financial markets alternate between periods of relative stability and instability, with structural breaks marking the transitions between these regimes. Identifying such breaks in real time is a central requirement for any trading or risk system operating at high frequency. This report studies Bayesian Online Changepoint Detection (BOCPD) and two extensions proposed in the literature, and applies them to the signed order flow of NASDAQ-listed equities.
 
 
 
 
 [5] 
 
 arXiv:2609.08060
 
 (cross-list from stat.AP)

 [ pdf , html , other ]
 
 
 
 Title: 
 Pre-game paired-comparison modeling of professional League of Legends map outcomes
 
 Min-Ren Guan , Shen-Ning Tung 

 Comments: 
 26 pages, 2 figures
 

 Subjects: 
 Applications (stat.AP) ; Statistical Finance (q-fin.ST)
 

 
 We build and evaluate a pre-game win-probability forecaster for individual maps (``games'') in professional \emph{League of Legends} (LoL). The proposed model is a one-stage logistic regression fit end-to-end on the win/loss log-loss: each team's exponentially-weighted moving average of past same-side results, a ridge-shrunk stable strength that is the maximum-a-posteriori estimate of a logistic mixed model, and a first-pick draft covariate, natively calibrated out of sample (walk-forward slope $0.995$). It augments a purely dynamic Bradley--Terry specification with stable team strengths. A second, independently built two-stage composite mixed model under restricted maximum likelihood (REML) and best linear unbiased prediction (BLUP) shrinkage, with Platt calibration, serves as the strongest rival the authors could build. On $5{,}135$ games across six regional leagues and three international events (2024--2026), under paired per-game Diebold--Mariano inference, the two architectures are statistically indistinguishable on every protocol and window (global holdout $0.2230$ vs.\ $0.2257$; walk-forward $0.2207$ vs.\ $0.2215$), so the simpler model is preferred on parsimony, not accuracy; both improve on the classical dynamic benchmark ($0.2351$) by a clear margin and on the static fits ($0.2301$/$0.2268$) more modestly. Against Polymarket on $928$ matched maps, the forecasts are statistically indistinguishable from the market on its own per-game contracts, with a modest market edge concentrated on cross-region Worlds and series-decider maps.
 
 
 
 
 [6] 
 
 arXiv:2609.08106
 
 (cross-list from cs.LG)

 [ pdf , html , other ]
 
 
 
 Title: 
 Nyström Attention Matches Full Attention for Cross-Sectional Stock Prediction
 
 Kunhan Guo 

 Comments: 
 14 pages, 4 figures. A short version is under review at the TS-LIMITS workshop, NeurIPS 2026
 

 Subjects: 
 Machine Learning (cs.LG) ; Statistical Finance (q-fin.ST)
 

 
 MASTER's inter-stock multi-head attention -- the module responsible for modeling cross-sectional stock relationships -- accounts for 42.5% of model parameters and 25% of predictive value. We systematically decompose this module and uncover a surprising structure: the learned attention is near-uniform (perplexity 278/300), yet forcing exact uniformity eliminates all cross-sectional discrimination. Spectral analysis resolves this paradox: the deviation from uniformity is low-rank (effective rank ~65, top-10 modes capture 96.5% of energy), explaining why sparse approximations consistently fail while Nystrom low-rank attention (m=32 landmarks) matches full O(N^2) attention at O(mN) cost -- certified equivalent via TOST at both N=300 (5 seeds, Rank IC p=0.003) and N=800 (10 seeds, Rank IC p=0.034). Additional findings include: (i) attention anti-correlates with return similarity (Spearman rho = -0.614; on the industry-labeled subset, -0.645 unconditionally and -0.627 after controlling for industry, beta, and volatility), suggesting complementarity-seeking rather than correlation mining; (ii) all graph-based alternatives degrade performance, with hard masking worse than complete module removal; and (iii) at N ~ 3,500 with adapted architectures, no cross-stock module (GCN, Nystrom, or MASTER-style pipeline) significantly outperforms a per-stock LSTM baseline (n=4 seeds), indicating that the benefits observed at smaller scales do not trivially transfer. These results establish that the inter-stock attention's value resides in a compressible, dynamic, near-global redistribution that rewards low-rank approximation but resists sparsification.
 
 
 
 

 
 Replacement submissions (showing 1 of 1 entries) 

 
 [7] 
 
 arXiv:2606.14182
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Correlation emergence and the Epps effect in two coupled limit order books
 
 Chris Angstmann , Tim Gebbie 

 Comments: 
 16 pages, 1 figure, 7 appendices. Revised numerical implementation to conform to the fixed operational-time lattice and explicit calendar-time subordination, corrected numerical source and coupling treatment; the analytical results and main conclusions are unchanged. Reproducibility code: this https URL 
 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) ; Analysis of PDEs (math.AP); Statistical Finance (q-fin.ST)
 

 
 We give a unified analytic account of correlation emergence and the Epps effect in two coupled limit order books. The Epps effect is the empirical reduction in measured cross-asset log-return correlation at short aggregation scales, or equivalently the recovery of measured correlation as the aggregation interval increases. The model starts from a fixed-grid discrete random walk for order flow in operational time, with creation, cancellation and diffusion. A pair-trader coupling between the books is introduced at the level of order creation, and calendar time is imposed through separate observation clocks. We clarify how the operational-time model reduces to coupled reaction--diffusion equations with a moving reaction boundary defining the model log-mid-price. Using a regularised local-response representation of the coupling, we derive approximate closed-form expressions for realised correlations as a function of aggregation time. Here the Epps effect is shown to arise from two distinct mechanisms: asynchronous observation clocks (subordination), finite coupling response times, and their combination.
 
 
 
 

 Total of 7 entries 
 
 Showing up to 2000 entries per page:
 
 fewer 
 |
 more 
 |
 all 

 

 
 
 

 
 
 
 
 We gratefully acknowledge support from
 our major funders ,
 member institutions , ,
 and all contributors.
 
 
 About 
 · 
 Help 
 · 
 Contact 
 · 
 Subscribe 
 · 
 Copyright 
 · 
 Privacy 
 · 
 Accessibility 
 · 
 Operational Status (opens in new tab) 
 
 

 
 Major funding support from