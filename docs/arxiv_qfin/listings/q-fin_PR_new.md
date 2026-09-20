# Source: https://arxiv.org/list/q-fin.PR/new

**Fetched:** 2026-09-09T15:10:05.276182+00:00

---

Pricing of Securities 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 Skip to main content 
 
 
 
 
 

 
 
 

 
 
 
 
 
 
 

 
 
 
 
 
 Search
 
 Submit 
 Donate 
 
 Log in 
 
 

 
 
 
 Search arXiv 
 
 
 
 
 
 Press Enter to search · Advanced search 
 
 
 
 
 
 
 
 Pricing of Securities 

 
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

 

 
 New submissions (showing 2 of 2 entries) 

 
 [1] 
 
 arXiv:2609.05433
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Perpetual Futures for Stocks: The SpaceX Pre-IPO Market
 
 Aditya Gupta , Nick Polson 

 Subjects: 
 Pricing of Securities (q-fin.PR) 
 

 
 Robert Shiller proposed perpetual futures in 1993 to create derivative markets for assets that are illiquid or whose price cannot be observed directly, such as single family homes, human capital, and the consumer price index. The crypto markets later built the instrument for a different reason and with a different funding rule. We give a single no arbitrage result that nests both designs: the perpetual price is the present value of a benchmark flow discounted at the funding rate, so the funding rule chooses both the benchmark and the discount. We give a random time change representation in which the price is the expected spot at the first event of a clock whose intensity is the funding rate, use it to show that stochastic volatility moves the basis only through the carry, so a volatility risk premium and not volatility itself can break the peg, read price discovery as the convergence of a Doob martingale driven by a stochastic approximation, and give a segmented market equilibrium that makes the pre listing premium structural rather than behavioural. The June 2026 SpaceX pre-IPO market is the first large scale realization of the idea for an equity claim, and we find that the perpetual consensus forecast the secondary clearing price more accurately than the bookbuilt offer. We close with other equity applications.
 
 
 
 
 [2] 
 
 arXiv:2609.07169
 
 
 [ pdf , html , other ]
 
 
 
 Title: 
 Pricing and Hedging of Discretely Monitored Asian Options in the Volterra-Heston Model
 
 Gijs Custers , Sven Karbach , Martin Friesen 

 Subjects: 
 Pricing of Securities (q-fin.PR) ; Probability (math.PR)
 

 
 We develop semi-closed pricing formulas and lifted-model hedging methods for discretely monitored geometric and arithmetic Asian options in the Volterra-Heston stochastic volatility model. Exploiting the affine Volterra structure, we derive a tractable transform for the joint law of the terminal log-price and the discretely monitored geometric average. This transform yields semi-closed pricing formulas for geometric Asian options, which in turn provide effective control variates for Monte Carlo valuation of arithmetic Asian options. Under the stated real-moment and affine-transform hypotheses, we also derive the Galtchouk-Kunita-Watanabe decomposition for Fourier-representable payoffs and obtain a variance-optimal hedge in terms of the Riccati-Volterra equation and the forward-variance curve. Using N-factor Markovian approximations, we obtain a finite-dimensional numerical implementation for hedging Asian options. Our numerical experiments document factor convergence for a regular non-Markovian kernel and the effect of rebalancing frequency on hedging error. In the Heston benchmark, geometric Asian controls substantially reduce the variance of arithmetic-Asian price estimates and improve the finite-sample stability of regression-based hedging relative to direct regression.
 
 
 
 

 
 Cross submissions (showing 1 of 1 entries) 

 
 [3] 
 
 arXiv:2609.06137
 
 (cross-list from q-fin.CP)

 [ pdf , html , other ]
 
 
 
 Title: 
 Unbiased Monte Carlo Greeks for Discontinuous Payoffs
 
 Evgeny Lakshtanov 

 Subjects: 
 Computational Finance (q-fin.CP) ; Pricing of Securities (q-fin.PR)
 

 
 Pathwise differentiation of Monte Carlo estimators fails at payoff discontinuities, producing zero or biased sensitivities for barriers, autocallables, and digital options. The industry workaround --- smoothing the indicator functions --- introduces bias and requires per-product calibration. We derive a correction formula that restores unbiased Greeks without smoothing. For a payoff $F(Z,\theta)$ that is piecewise smooth with discontinuities on surfaces $\{g_i = 0\}$, we show that the sensitivity decomposes into a pathwise term (computed by standard AAD) plus a sum of boundary corrections, each involving the payoff jump, the Gaussian density at the boundary, and the sensitivity of the boundary to the parameter. The correction is computed by Newton root-finding in the normal-random space, with the jump evaluated by two forward replays of the pricing kernel. The implementation uses AADC (\texttt{pip install aadc}), whose tape replay and automatic discontinuity tracking make the method fully automatic --- the quant writes standard pricing code, and the correction driver identifies and handles all discontinuities. We prove the formula for arbitrary compositions of smooth functions and indicator functions (not just outer products), covering real autocallable payoff structures with recursive alive/dead logic. Benchmarks on QuantLib models (GBM, Heston, Hull-White) show all Greeks within 0.1--4\% of analytic or bump-and-revalue references.
 
 
 
 

 
 Replacement submissions (showing 4 of 4 entries) 

 
 [4] 
 
 arXiv:1502.05743
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 The existence of optimal bang-bang controls for GMxB contracts
 
 Parsiad Azimzadeh , Peter A. Forsyth 

 Comments: 
 Fixed conditioning typo in (2.3), (2.13). Handled x2=0 in Ex. 4.20. Added nonemptiness to Lemmas 4.11, B.1. Added endpoint condition to Thm. A.4. Corrected various typos. Main results, numerics, and figures unchanged. Minor bib/LaTeX updates
 

 Journal-ref: 
 SIAM.J.Finan.Math. 6.1 (2015) 117-139
 

 Subjects: 
 Pricing of Securities (q-fin.PR) 
 

 
 A large collection of financial contracts offering guaranteed minimum benefits are often posed as control problems, in which at any point in the solution domain, a control is able to take any one of an uncountable number of values from the admissible set. Often, such contracts specify that the holder exert control at a finite number of deterministic times. The existence of an optimal bang-bang control, an optimal control taking on only a finite subset of values from the admissible set, is a common assumption in the literature. In this case, the numerical complexity of searching for an optimal control is considerably reduced. However, no rigorous treatment as to when an optimal bang-bang control exists is present in the literature. We provide the reader with a bang-bang principle from which the existence of such a control can be established for contracts satisfying some simple conditions. The bang-bang principle relies on the convexity and monotonicity of the solution and is developed using basic results in convex analysis and parabolic partial differential equations. We show that a guaranteed lifelong withdrawal benefit (GLWB) contract admits an optimal bang-bang control. In particular, we find that the holder of a GLWB can maximize a writer's losses by only ever performing nonwithdrawal, withdrawal at exactly the contract rate, or full surrender. We demonstrate that the related guaranteed minimum withdrawal benefit contract is not convexity preserving, and hence does not satisfy the bang-bang principle other than in certain degenerate cases.
 
 
 
 
 [5] 
 
 arXiv:2506.08067
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Smile asymptotics for Bachelier implied volatility
 
 Roberto Baviera , Michele Domenico Massaria 

 Subjects: 
 Pricing of Securities (q-fin.PR) ; Probability (math.PR); Mathematical Finance (q-fin.MF)
 

 
 We investigate the asymptotic behaviour of the Bachelier implied volatility tails, extending the large-strike results established for the Black-Scholes implied volatility. Exploiting the theory of regular variation, we derive explicit expressions for the Bachelier implied volatility in the wings of the smile, directly linking them to the tail decay of the underlying returns' distribution. Furthermore, we establish a rigorous connection between the analyticity strip of the characteristic function and the asymptotic slope of the volatility smile. Moreover, we show that if the implied variance grows linearly for large absolute moneyness degree, the underlying returns' distribution must exhibit exponential tail decay, and the corresponding characteristic function is analytic in a horizontal strip of the complex plane. These findings characterise valid models based solely on the observable asymptotic behaviour of the smile.
 
 
 
 
 [6] 
 
 arXiv:2603.24605
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 Bid--Ask Martingale Optimal Transport
 
 Bryan Liang , Marcel Nutz , Shunan Sheng , Valentin Tissot-Daguette 

 Comments: 
 45 pages
 

 Subjects: 
 Mathematical Finance (q-fin.MF) ; Functional Analysis (math.FA); Optimization and Control (math.OC); Probability (math.PR); Pricing of Securities (q-fin.PR)
 

 
 Martingale Optimal Transport (MOT) provides a framework for robust pricing and hedging of illiquid derivatives. Classical MOT enforces exact calibration of model marginals to the mid-prices of vanilla options. Motivated by the industry practice of fitting bid and ask marginals to vanilla prices, we introduce a relaxation of MOT in which model-implied volatilities are only required to lie within observed bid--ask spreads; equivalently, model marginals lie between the bid and ask marginals in convex order. The resulting Bid--Ask MOT (BAMOT) yields realistic price bounds for illiquid derivatives and, via strong duality, can be interpreted as the superhedging price when short and long positions in vanilla options are priced at the bid and ask, respectively. We further establish convergence of BAMOT to classical MOT as bid--ask spreads vanish, and quantify the convergence rate using a novel distance intrinsically linked to bid--ask spreads. Finally, we support our findings with several synthetic and real-data examples.
 
 
 
 
 [7] 
 
 arXiv:2608.13732
 
 (replaced)

 [ pdf , html , other ]
 
 
 
 Title: 
 On the First Hitting Time Problems for Diffusion Processes: Local Time-Space Approach
 
 Jerome Detemple , Yerkin Kitapbayev , Danila Shabalin 

 Subjects: 
 Probability (math.PR) ; Computational Finance (q-fin.CP); Pricing of Securities (q-fin.PR)
 

 
 Using the local time-space calculus of Peskir (2005) and the method developed in Mijatovic (2010), we derive a new integral representation for the distribution of the first-passage time (FPT) of a diffusion process through a time-dependent barrier. We present a complete three-step numerical algorithm: first, the problem is reduced to a Volterra-type integral equation; second, its kernel is approximated by a Markov chain; finally, the resulting equation is solved using a quadrature method. The method is implemented for several representative examples, and its convergence properties are established. An extension to double barrier problems is carried out.
 
 
 
 

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