# Source: https://arxiv.org/list/q-fin.TR/new

**Fetched:** 2026-09-09T15:10:20.894707+00:00

---

Trading and Market Microstructure 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 Skip to main content 
 
 
 
 
 

 
 
 

 
 
 
 
 
 
 

 
 
 
 
 
 Search
 
 Submit 
 Donate 
 
 Log in 
 
 

 
 
 
 Search arXiv 
 
 
 
 
 
 Press Enter to search · Advanced search 
 
 
 
 
 
 
 
 Trading and Market Microstructure 

 
 New submissions 
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

 

 
 New submissions (showing 3 of 3 entries) 

 
 [1] 
 
 arXiv:2609.06085
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Explainable Deep Learning for Price-Trade Dynamics: From Black-Box Forecasts to Effective Parametric Models
 
 Manuel Naviglio , Fabrizio Lillo 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) ; Artificial Intelligence (cs.AI); Data Analysis, Statistics and Probability (physics.data-an)
 

 
 Understanding the joint dynamics of prices and trades is central to market microstructure, where returns and order flow interact through nonlinear and state-dependent mechanisms. Linear models are interpretable but may miss these effects, while deep neural networks improve forecasting at the cost of transparency. We use neural networks as tools for structural discovery rather than only for prediction. A deep feed-forward network is trained on high-frequency returns and signed volumes for large- and small-tick stocks and compared with a linear VAR benchmark. The neural network improves predictive performance, especially for returns, revealing nonlinear dependencies beyond the linear specification. Using Shapley-based explainability, we show that the dominant contributions are concentrated at the most recent lags. Model-implied responses are consistent with conditional averages reconstructed from the data. Unlike empirical averages, however, the neural-network decomposition isolates individual regressor contributions to the aggregate dependence. Lagged signed volume generates sign-preserving and saturating effects, consistent with nonlinear price impact and order-flow persistence. Lagged returns act as state variables: when the previous trade does not move the price, the model predicts continuation in the direction of past order flow, whereas non-zero returns generate attenuation or reversal. Building on these findings, we introduce a parsimonious SHAP-inspired nonlinear parametric model. It reproduces the main return-volume dependencies, outperforms the linear VAR benchmark, and achieves performance comparable to the neural network. A multi-lag extension captures residual longer-memory effects while preserving interpretability. Overall, explainability offers a route from black-box prediction to economically meaningful parametric models of price and trade dynamics.
 
 
 
 
 [2] 
 
 arXiv:2609.07989
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Regimes in the Order Flow
 
 Ramzi Jebali 

 Comments: 
 59 pages. 48 figures. Summer research project of ENSTA at Scuola Normale Superiore (Pisa)
 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) ; Computational Finance (q-fin.CP); Mathematical Finance (q-fin.MF); Statistical Finance (q-fin.ST)
 

 
 Financial markets alternate between periods of relative stability and instability, with structural breaks marking the transitions between these regimes. Identifying such breaks in real time is a central requirement for any trading or risk system operating at high frequency. This report studies Bayesian Online Changepoint Detection (BOCPD) and two extensions proposed in the literature, and applies them to the signed order flow of NASDAQ-listed equities.
 
 
 
 
 [3] 
 
 arXiv:2609.08881
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 The Double-Edged Sword of Short-Selling Bans
 
 Pasquale Della Corte , Robert Kosowski , Dimitris Papadimitriou , Nikolaos P. Rapanos 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) 
 

 
 We develop a theoretical model that endogenizes the regulator's decision to impose short-selling bans to prevent large stock price declines. Empirically, we test the model's predictions using the cross-sectional variation in short-selling restrictions implemented across European countries in 2020. Consistent with our model, we find that bans had a detrimental effect on liquidity and failed to support the average price levels, but were effective in limiting large price drawdowns. Finally, we show that the effectiveness of the bans depends on the share of informed stockholders, a central variable in our framework, thus informing the design of more effective regulatory responses.
 
 
 
 

 
 Replacement submissions (showing 4 of 4 entries) 

 
 [4] 
 
 arXiv:2512.23515
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Alpha-R1: Alpha Screening with LLM Reasoning via Reinforcement Learning
 
 Zuoyou Jiang , Li Zhao , Rui Sun , Ruohan Sun , Zhongjian Li , Jing Li , Daxin Jiang , Zuo Bai , Cheng Hua 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) ; Artificial Intelligence (cs.AI); Computational Engineering, Finance, and Science (cs.CE); Machine Learning (cs.LG)
 

 
 Signal decay and regime shifts pose recurring challenges for data-driven investment strategies in non-stationary markets, where conventional time-series and machine learning approaches often struggle to generalize beyond historical correlations. While large language models (LLMs) offer strong capabilities for processing unstructured information, their potential to support quantitative factor screening through explicit economic reasoning remains underexplored. Existing factor-based methods typically reduce alphas to numerical time series, overlooking the semantic rationale that determines when a factor is economically relevant. We present Alpha-R1, an RL-aligned LLM framework for context-aware alpha screening. Its core mechanism, semantic gating, evaluates each candidate factor's semantic profile against a dynamically constructed market state description, selecting a sparse subset of factors whose economic rationale aligns with current market conditions. The selection model is trained via group relative policy optimization (GRPO), using realized portfolio returns as the primary reward signal. Under a 12-month out-of-sample evaluation, Alpha-R1 achieves annualized returns of 47.87% on S&P 500 and 40.57% on CSI 300 with Sharpe ratios of 1.62 and 2.23. These results, obtained under a bounded candidate-pool evaluation protocol, provide evidence for second-stage semantic factor reranking in non-stationary markets. The full implementation and resources are available at this https URL .
 
 
 
 
 [5] 
 
 arXiv:2606.07059
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Diffusive in plain sight: An inconspicuous law of market impact
 
 Julius F. Bonart 

 Subjects: 
 Trading and Market Microstructure (q-fin.TR) 
 

 
 Decomposing market impact as the difference between realized and counterfactual returns, and requiring both to be diffusive, yields a structural identity that restricts admissible impact dynamics at the level of individual participants. This constraint implies the square-root law in the information-neutral regime and a crossover toward linear impact under strong informational coupling, consistent with empirical observations. It further implies that impact must adapt to each participant's order-flow statistics, with consequences for theories of optimal execution and no-arbitrage. In the information-neutral regime, cumulative impact is itself diffusive, providing a diagnostic that many propagator and latent-liquidity models fail to satisfy. Under this regime, market impact retains an undetermined all-pass degree of freedom that prevents its reduction to a pure surprise model. This residual freedom accommodates transient impact dynamics and can generate strictly positive impact costs.
 
 
 
 
 [6] 
 
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
 
 
 
 
 [7] 
 
 arXiv:2601.02310
 
 (replaced)

 [ pdf , other ]
 
 
 
 Title: 
 Temporal Kolmogorov-Arnold Networks (T-KAN) for High-Frequency Limit Order Book Forecasting: Efficiency, Interpretability, and Alpha Decay
 
 Ahmad Makinde 

 Comments: 
 8 pages, 5 figures, Proposes T-KAN architecture for HFT. Achieves 19.1% F1-score improvement on FI-2010 and 132.48% return in cost-adjusted this http URL T-KAN architecture for HFT. Achieves 19.1% F1-score improvement on FI-2010 and 132.48% return in cost-adjusted backtests
 

 Journal-ref: 
 BILT Student Research Journal, Issue 7, 2026
 

 Subjects: 
 Machine Learning (cs.LG) ; Trading and Market Microstructure (q-fin.TR)
 

 
 High-Frequency trading (HFT) environments are characterised by large volumes of limit order book (LOB) data, which is notoriously noisy and non-linear. Alpha decay represents a significant challenge, with traditional models such as DeepLOB losing predictive power as the time horizon (k) increases. In this paper, using data from the FI-2010 dataset, we introduce Temporal Kolmogorov-Arnold Networks (T-KAN) to replace the fixed, linear weights of standard LSTMs with learnable B-spline activation functions. This allows the model to learn the 'shape' of market signals as opposed to just their magnitude. This resulted in a 19.1% relative improvement in the F1-score at the k = 100 horizon. The efficacy of T-KAN networks cannot be understated, producing a 132.48% return compared to the -82.76% DeepLOB drawdown under 1.0 bps transaction costs. In addition to this, the T-KAN model proves quite interpretable, with the 'dead-zones' being clearly visible in the splines. The T-KAN architecture is also uniquely optimized for low-latency FPGA implementation via High level Synthesis (HLS). The code for the experiments in this project can be found at this https URL .
 
 
 
 

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