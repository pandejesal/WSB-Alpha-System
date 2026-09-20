# Source: https://arxiv.org/list/q-fin.CP/new

**Fetched:** 2026-09-09T15:09:39.089955+00:00

---

Computational Finance 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 Skip to main content 
 
 
 
 
 

 
 
 

 
 
 
 
 
 
 

 
 
 
 
 
 Search
 
 Submit 
 Donate 
 
 Log in 
 
 

 
 
 
 Search arXiv 
 
 
 
 
 
 Press Enter to search · Advanced search 
 
 
 
 
 
 
 
 Computational Finance 

 
 New submissions 
 Cross-lists 
 Replacements 
 

 See recent articles 
 Showing new listings for Wednesday, 9 September 2026 

 Total of 11 entries 
 
 Showing up to 2000 entries per page:
 
 fewer 
 |
 more 
 |
 all 

 

 
 New submissions (showing 3 of 3 entries) 

 
 [1] 
 
 arXiv:2609.05434
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Deep Learning for Reflected BSDEs: Regularization and Error Analysis
 
 Ruimeng Hu , Yihan Zou 

 Comments: 
 26 pages
 

 Subjects: 
 Computational Finance (q-fin.CP) ; Machine Learning (stat.ML)
 

 
 Reflected backward stochastic differential equations (RBSDEs) provide a probabilistic formulation for obstacle constrained problems, but existing deep learning methods for their high dimensional solution remain limited. In this paper, we propose two deep learning schemes for RBSDEs, a deep forward scheme (DFS) and a deep backward scheme (DBS), by first reducing the reflected problem to a family of regularized BSDEs. Our main theoretical contribution concerns the DBS: we establish an explicit error bound showing that, for each fixed regularization parameter $\varepsilon>0$, the approximation error between the DBS solution and the solution to the regularized BSDE is controlled by the associated training loss. We prove that this training loss can be controlled by the universal approximation capability of neural networks. Together, these results yield a theoretical foundation for the deep learning-based solution and complement existing analysis for forward type methods. We illustrate the framework on high dimensional American option pricing, where the reflected formulation allows us to address the continuous time exercise feature directly rather than through a Bermudan approximation. Numerical experiments demonstrate that both DFS and DBS deliver accurate solutions in high dimensions.
 
 
 
 
 [2] 
 
 arXiv:2609.05491
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Asymptotically-informed neural networks for Black-Scholes implied volatility computation
 
 Samira Amiriyan , Youness Boutaib 

 Subjects: 
 Computational Finance (q-fin.CP) ; Machine Learning (cs.LG); Machine Learning (stat.ML)
 

 
 The computation of Black-Scholes implied volatility is a fundamental task in quantitative finance, underpinning option valuation, model calibration and risk management. Although implied volatility is routinely used in practice, the inversion of the Black-Scholes pricing formula remains a challenging numerical problem, particularly in asymptotic regimes corresponding to extreme option prices, strikes or maturities, where the inverse map becomes highly sensitive to perturbations of the price. In this paper, we introduce a new family of asymptotically-informed neural-network architectures for implied-volatility computation. Exploiting the distinct behaviours of the Black-Scholes pricing function in different volatility regimes, we propose a family of architectures that learn a trainable partition of the price-log-moneyness domain through a system of gating functions and combines specialised local approximations of the implied-volatility function within each region. Extensive numerical experiments demonstrate that the proposed models consistently outperform standard feed-forward neural networks across a wide range of parameter domains, often by several orders of magnitude in relative accuracy while maintaining excellent generalisation properties. Furthermore, the neural-network outputs provide highly accurate initial guesses for a third-order Householder scheme, allowing near machine-precision implied-volatility computations after only two refinement iterations.
 
 
 
 
 [3] 
 
 arXiv:2609.06137
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Unbiased Monte Carlo Greeks for Discontinuous Payoffs
 
 Evgeny Lakshtanov 

 Subjects: 
 Computational Finance (q-fin.CP) ; Pricing of Securities (q-fin.PR)
 

 
 Pathwise differentiation of Monte Carlo estimators fails at payoff discontinuities, producing zero or biased sensitivities for barriers, autocallables, and digital options. The industry workaround --- smoothing the indicator functions --- introduces bias and requires per-product calibration. We derive a correction formula that restores unbiased Greeks without smoothing. For a payoff $F(Z,\theta)$ that is piecewise smooth with discontinuities on surfaces $\{g_i = 0\}$, we show that the sensitivity decomposes into a pathwise term (computed by standard AAD) plus a sum of boundary corrections, each involving the payoff jump, the Gaussian density at the boundary, and the sensitivity of the boundary to the parameter. The correction is computed by Newton root-finding in the normal-random space, with the jump evaluated by two forward replays of the pricing kernel. The implementation uses AADC (\texttt{pip install aadc}), whose tape replay and automatic discontinuity tracking make the method fully automatic --- the quant writes standard pricing code, and the correction driver identifies and handles all discontinuities. We prove the formula for arbitrary compositions of smooth functions and indicator functions (not just outer products), covering real autocallable payoff structures with recursive alive/dead logic. Benchmarks on QuantLib models (GBM, Heston, Hull-White) show all Greeks within 0.1--4\% of analytic or bump-and-revalue references.
 
 
 
 

 
 Cross submissions (showing 2 of 2 entries) 

 
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
 
 arXiv:2609.08581
 
 (cross-list from cs.LG)

 [ pdf , html , other ]
 
 
 
 Title: 
 AlphaRJM: Reward-Jump Memory for Stochastic Return-Guided Alpha Discovery
 
 Sayan Dhan , Selvaraju Natarajan 

 Comments: 
 26 pages,5 Tables, 4 Figures
 

 Subjects: 
 Machine Learning (cs.LG) ; Computational Finance (q-fin.CP); Machine Learning (stat.ML)
 

 
 Formulaic alpha discovery is a pool-dependent symbolic search problem in which informative feedback is observed primarily when a complete expression is evaluated. This delayed feedback creates two coupled difficulties: the retained alpha pool does not preserve the full history of realized evaluation feedback, and the value of an intermediate construction action is uncertain because its consequence depends on the formula eventually completed. We introduce AlphaRJM, which addresses these difficulties through Reward-Jump Memory, an event-driven latent state that remains fixed during token construction and updates only at terminal evaluation events using the realized pool reward and evaluation outcome, and an action-conditioned SDE return critic that represents future discounted discovery returns with stochastic particles. The particles guide action selection through their mean and uncertainty and are learned using a distributional Bellman objective combining energy-distance matching, mean calibration, and jump regularization. Empirically, AlphaRJM delivers strong and stable gains across multiple equity universes, forecasting horizons, and random seeds, while ablations confirm the complementary roles of persistent evaluation history, stochastic return modeling, and distributional supervision.
 
 
 
 

 
 Replacement submissions (showing 6 of 6 entries) 

 
 [6] 
 
 arXiv:2601.07131
 
 (replaced)

 [ pdf , other ]
 
 
 
 Title: 
 The Limits of Complexity: Why Feature Engineering Beats Deep Learning in Investor Flow Prediction
 
 Sungwoo Kang 

 Comments: 
 This paper has been withdrawn by the author due to an implementation error that resulted in look-ahead bias (data leakage)
 

 Subjects: 
 Computational Finance (q-fin.CP) 
 

 
 The application of machine learning to financial prediction has accelerated dramatically, yet the conditions under which complex models outperform simple alternatives remain poorly understood. This paper investigates whether advanced signal processing and deep learning techniques can extract predictive value from investor order flows beyond what simple feature engineering achieves. Using a comprehensive dataset of 2.79 million observations spanning 2,439 Korean equities from 2020--2024, we apply three methodologies: \textit{Independent Component Analysis} (ICA) to recover latent market drivers, \textit{Wavelet Coherence} analysis to characterize multi-scale correlation structure, and \textit{Long Short-Term Memory} (LSTM) networks with attention mechanisms for non-linear prediction. Our results reveal a striking finding: a parsimonious linear model using market capitalization-normalized flows (``Matched Filter'' preprocessing) achieves a Sharpe ratio of 1.30 and cumulative return of 272.6\%, while the full ICA-Wavelet-LSTM pipeline generates a Sharpe ratio of only 0.07 with a cumulative return of $-5.1\%$. The raw LSTM model collapsed to predicting the unconditional mean, achieving a hit rate of 47.5\% -- worse than random. We conclude that in low signal-to-noise financial environments, domain-specific feature engineering yields substantially higher marginal returns than algorithmic complexity. These findings establish important boundary conditions for the application of deep learning to financial prediction.
 
 
 
 
 [7] 
 
 arXiv:2605.06604
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 A Geometry-Aware Residual Correction of Hagan's SABR Implied Volatility Formula
 
 Adil Reghai , Lama Tarsissi , Gérard Biau , Alex Lipton 

 Comments: 
 33 pages, 17 figures
 

 Subjects: 
 Computational Finance (q-fin.CP) ; Machine Learning (stat.ML)
 

 
 This paper proposes a hybrid methodology to improve the approximation of SABR (Stochastic Alpha Beta Rho) implied volatility by combining analytical structure with machine learning. The approach augments the neural-network input representation with geometric features derived from the stochastic differential equations of the SABR model. Unlike approaches that fully replace analytical formulas with black-box models, the proposed framework preserves the analytical backbone of the model. The hybridization operates along two complementary dimensions. First, geometry-aware variables reflecting intrinsic properties of the SABR dynamics are used as structured inputs to the network. Second, the neural network is trained to learn the residual error relative to Hagan's closed-form approximation rather than implied volatility directly. The resulting model acts as a structured residual correction to the analytical formula, retaining interpretability while capturing higher-order effects that are not included in the asymptotic expansion. Numerical experiments conducted over realistic parameter domains, as well as stressed environments, show that the method improves accuracy and robustness compared with both analytical approximations and standard neural-network approaches. Because the correction remains lightweight and structurally consistent with the underlying model, the framework is well suited for real-time pricing and calibration in practical trading environments.
 
 
 
 
 [8] 
 
 arXiv:1510.03928
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Weakly chained matrices, policy iteration, and impulse control
 
 Parsiad Azimzadeh , Peter A. Forsyth 

 Comments: 
 Changed Sec. 6.1 to study a two-sided intervention problem. Made minor corrections to Sec. 5.3 boundary term and proofs of Lemmas 4.1/4.6. Required X to be nonempty in Lemma A.2. Main theoretical results unchanged. Minor bib/LaTeX updates
 

 Journal-ref: 
 SIAM.J.Numer.Anal. 54.3 (2016) 1341-1364
 

 Subjects: 
 Numerical Analysis (math.NA) ; Computational Finance (q-fin.CP)
 

 
 This work is motivated by numerical solutions to Hamilton-Jacobi-Bellman quasi-variational inequalities (HJBQVIs) associated with combined stochastic and impulse control problems. In particular, we consider (i) direct control, (ii) penalized, and (iii) semi-Lagrangian discretization schemes applied to the HJBQVI problem. Scheme (i) takes the form of a Bellman problem involving an operator which is not necessarily contractive. We consider the well-posedness of the Bellman problem and give sufficient conditions for convergence of the corresponding policy iteration. To do so, we use weakly chained diagonally dominant matrices, which give a graph-theoretic characterization of nonsingular weakly diagonally dominant M-matrices. We compare schemes (i)--(iii) under the following examples: (a) optimal control of the exchange rate, (b) optimal consumption with fixed and proportional transaction costs, and (c) pricing guaranteed minimum withdrawal benefits in variable annuities. We find that one should abstain from using scheme (i).
 
 
 
 
 [9] 
 
 arXiv:2607.12990
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 A Noise-Aware Quantum Algorithm for Credit Valuation Adjustments on Real Quantum Hardware
 
 Guillem Borràs Espert , Francisco Gómez Casanova , Luis de Pedro Sánchez , Senaida Hernández Santana , Pablo Serrano Molinero 

 Comments: 
 56 pages, 14 figures, 18 tables. Includes supplementary appendices with implementation details, extended results, calibration data, and quantum-resource analysis
 

 Subjects: 
 Quantum Physics (quant-ph) ; Computational Finance (q-fin.CP)
 

 
 Credit Valuation Adjustment (CVA) requires repeated risk-neutral expectation estimation, making it a natural test bed for quantum amplitude estimation, whose coherent amplification can in principle reduce Monte Carlo sampling cost. Whether this advantage survives realistic financial encoding and noisy hardware remains open. We develop an end-to-end, noise-aware quantum workflow for CVA, covering market calibration, discretisation, oracle construction, hardware execution and error-budget analysis. The model combines a correlated two-asset exposure with discount and default factors, encoded through a QCBM-based joint time-market distribution and controlled payoff rotations. We introduce contrast-aware Bayesian iterative quantum amplitude estimation (CABIQAE), which incorporates experimentally calibrated Grover-contrast loss into Bayesian inference and circuit-depth selection. Hardware-calibrated experiments show that CABIQAE exploits the limited amplification available on current devices more effectively than noise-agnostic alternatives and achieves a much lower classical post-processing runtime than the noise-aware BAE baseline. The analysis further decomposes the total CVA error into statistical, encoding, discretisation and hardware contributions. The full CVA oracle remains limited by circuit depth and discretisation resolution.
 
 
 
 
 [10] 
 
 arXiv:2608.13732
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 On the First Hitting Time Problems for Diffusion Processes: Local Time-Space Approach
 
 Jerome Detemple , Yerkin Kitapbayev , Danila Shabalin 

 Subjects: 
 Probability (math.PR) ; Computational Finance (q-fin.CP); Pricing of Securities (q-fin.PR)
 

 
 Using the local time-space calculus of Peskir (2005) and the method developed in Mijatovic (2010), we derive a new integral representation for the distribution of the first-passage time (FPT) of a diffusion process through a time-dependent barrier. We present a complete three-step numerical algorithm: first, the problem is reduced to a Volterra-type integral equation; second, its kernel is approximated by a Markov chain; finally, the resulting equation is solved using a quadrature method. The method is implemented for several representative examples, and its convergence properties are established. An extension to double barrier problems is carried out.
 
 
 
 
 [11] 
 
 arXiv:2608.17808
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Self-Consistent Adjoint Policy Iteration for Constrained Dynamic Portfolio Choice
 
 Jeonggyu Huh , Yeoneung Kim , Seungwon Jeong 

 Subjects: 
 Optimization and Control (math.OC) ; Computational Finance (q-fin.CP); Portfolio Management (q-fin.PM)
 

 
 We develop simulation-based policy iteration for continuous-time portfolio choice with predictable returns and convex constraints. Each outer step re-evaluates a fixed-latent open-loop backpropagation-through-time (OL-BPTT) adjoint after deployment and solves the constrained update. Shifted-adjoint cancellation controls the adjoint--HJB Hamiltonian-gradient discrepancy by the policy-improvement residual. For CRRA portfolios, exact HJB policy iteration identifies the optimal reduced value factor, while population OL-BPTT iteration converges globally when the adjoint update is directionally improving and approximate stationarity is asymptotically HJB-compatible. A theorem-matched occupation audit yields maximal $95\%$ upper endpoints of $0.066$ for the primitive directional ratio and $0.074$ for a stronger norm-relative ratio, both against the half-step threshold $0.75$. In the high-precision $50$--$50$ occupancy/broad-anchor design of a three-factor, fifty-asset benchmark, current-policy re-evaluation outperforms matched pooled refinement under the on-policy and broad evaluation laws.
 
 
 
 

 Total of 11 entries 
 
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