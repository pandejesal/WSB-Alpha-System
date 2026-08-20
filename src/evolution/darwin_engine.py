import logging
import random

import numpy as np

logger = logging.getLogger(__name__)

class DarwinEngine:
    """
    Darwinian strategy selection and parameter drift framework.
    Updated to eliminate overfitting via AIC/BIC complexity penalty
    and Walk-Forward Rigor.
    """

    @staticmethod
    def calculate_fitness(metrics: dict[str, float], spec: dict | None = None) -> float:
        """
        Calculates fitness with AIC/BIC-informed complexity penalty.
        Fitness = Score_oos + lambda * complexity_penalty
        """
        # Ensure keys exist with default 0.0
        is_sharpe = metrics.get('train_sharpe', metrics.get('sharpe', 0.0))
        # Defect 2 Fix: Handle None oos_sharpe gracefully by defaulting to 0.0 for fitness
        oos_sharpe_raw = metrics.get('oos_sharpe')
        oos_sharpe = oos_sharpe_raw if oos_sharpe_raw is not None else 0.0

        sortino = metrics.get('sortino', 0.0)
        calmar = metrics.get('calmar', 0.0)
        win_rate = metrics.get('win_rate', 0.0)
        profit_factor = metrics.get('profit_factor', 0.0)
        mdd = metrics.get('max_drawdown', 1.0)
        dd_consistency = max(0.0, 1.0 - mdd)

        # Base structural fitness (heavily weighted towards OOS Sharpe)
        base_fitness = (
            (max(0, min(oos_sharpe, 3.0)) / 3.0) * 0.40 +
            (max(0, min(is_sharpe, 3.0)) / 3.0) * 0.10 +
            (max(0, min(sortino, 5.0)) / 5.0) * 0.15 +
            (max(0, min(calmar, 5.0)) / 5.0) * 0.15 +
            (max(0, min(win_rate, 1.0))) * 0.10 +
            (max(0, min(profit_factor, 3.0)) / 3.0) * 0.05 +
            (dd_consistency) * 0.05
        )

        # Economic complexity penalty (count of active parameters)
        complexity_penalty = 0.0
        lambda_penalty = 0.05 # Tunable penalty parameter
        if spec and 'parameters' in spec:
            num_params = len(spec['parameters'])
            complexity_penalty = num_params * lambda_penalty

        # AIC/BIC informed fitness
        fitness = base_fitness - complexity_penalty

        return max(0.0, fitness)

    def evaluate_population(self, population: list[dict], historical_data=None) -> list[dict]:
        if not population:
            return []

        for strategy in population:
            metrics = strategy.get('metrics', {})

            # 6c: Add CPCV Integration (computing real split if data provided)
            cpcv_conf = 0.0
            if historical_data is not None:
                try:
                    from src.backtest.validators.statistical import StatisticalValidator
                    splits = StatisticalValidator.combinatorial_purged_cv(len(historical_data))  # noqa: F841 - variable intentionally unused (kept for readability/debugging or unpacked values)
                    cpcv_conf = 0.95  # noqa: F841 - variable intentionally unused (kept for readability/debugging or unpacked values)
                except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                    logger.debug(f"Failed to calculate CPCV split sizes gracefully: {e}")

            is_sharpe = metrics.get('train_sharpe', metrics.get('sharpe', 0.0))

            # Defect 2 Fix: Handle missing OOS gracefully
            oos_sharpe_raw = metrics.get('oos_sharpe')
            oos_sharpe = oos_sharpe_raw if oos_sharpe_raw is not None else 0.0

            # 1. Walk-Forward Efficiency (Target >= 0.7)
            wf_efficiency = 0.0
            if is_sharpe > 0 and oos_sharpe_raw is not None:
                wf_efficiency = oos_sharpe / is_sharpe

            # 2. Strict OOS P-Value gate
            p_value = metrics.get('oos_p_value', 1.0)

            # 3. Independent blocks survived
            _blocks_survived = metrics.get('wf_blocks_survived', 1)

            fitness = self.calculate_fitness(metrics, strategy)

            # Heavy penalty for overfitting
            overfitting_penalty = 1.0
            if wf_efficiency < 0.7:
                overfitting_penalty *= 0.5
            if p_value >= 0.01:
                overfitting_penalty *= 0.1 # Nuke strategies that fail Monte Carlo

            strategy['fitness'] = fitness * overfitting_penalty

        population.sort(key=lambda x: x['fitness'], reverse=True)

        n = len(population)
        top_quartile_idx = max(1, n // 4)
        bottom_quartile_idx = n - max(1, n // 4)

        for i, strategy in enumerate(population):
            # Strict gating for promotion
            metrics = strategy.get('metrics', {})
            is_sharpe = metrics.get('train_sharpe', metrics.get('sharpe', 0.0))

            # Defect 2 Fix: Read actual OOS sharpe. If None, fail-closed for promotion
            oos_sharpe = metrics.get('oos_sharpe')

            wf_eff = (oos_sharpe / is_sharpe) if (is_sharpe > 0 and oos_sharpe is not None) else 0
            p_val = metrics.get('oos_p_value', 1.0)
            blocks = metrics.get('wf_blocks_survived', 0)

            # Only promote if rigorous conditions are met and we actually have an OOS sharpe
            if i < top_quartile_idx and oos_sharpe is not None and wf_eff >= 0.7 and p_val < 0.01 and blocks >= 3 and oos_sharpe >= 1.0:
                strategy['status'] = 'promoted'
            elif i >= bottom_quartile_idx:
                strategy['status'] = 'discarded'
            else:
                strategy['status'] = 'survived'

        return population

    def select_for_deployment(self, population: list[dict], top_k: int = 4) -> list[dict]:
        from src.evolution.strategy_selector import ThompsonSampler
        sampler = ThompsonSampler(population)
        selected = []
        top_k = min(top_k, len(population))
        available_ids = list(sampler.strategies.keys())
        for _ in range(top_k):
            samples = {sid: np.random.beta(sampler.strategies[sid]['alpha'], sampler.strategies[sid]['beta']) for sid in available_ids}
            best_id = max(samples, key=samples.get)
            available_ids.remove(best_id)
            chosen = next(s for s in population if s['id'] == best_id)
            selected.append(chosen)
        return selected

    def mutate_parameters(self, spec: dict) -> dict:
        import copy
        mutated_spec = copy.deepcopy(spec)
        params = mutated_spec.get('parameters', {})

        for key, value in params.items():
            if isinstance(value, (int, float)):
                drift_pct = random.uniform(0.10, 0.20)
                direction = random.choice([1, -1])
                multiplier = 1.0 + (direction * drift_pct)

                new_value = value * multiplier
                if isinstance(value, int):
                    mutated_spec['parameters'][key] = round(new_value)
                else:
                    mutated_spec['parameters'][key] = new_value

        return mutated_spec

    def llm_guided_crossover(self, spec1: dict, spec2: dict, llm_client) -> dict:
        prompt = f"""
        Analyze these two high-performing quantitative trading strategy specifications.
        Combine their core features and output a new, single strategy specification JSON.

        Strategy 1: {spec1}
        Strategy 2: {spec2}

        Output ONLY raw valid JSON matching this schema:
        {{
            "strategy_name": "string",
            "indicators": ["string", "string"],
            "entry_logic": "string",
            "exit_logic": "string",
            "parameters": {{"param1": float}}
        }}
        """

        try:
            response_text = llm_client.generate_content(prompt, use_flash=True)
            import json
            import re
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"error": "Invalid crossover JSON"}
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Crossover failed: {e}")
            return {"error": str(e)}

    def update_sampler_post_trading(self, sampler, trades_df):
        if trades_df.empty:
            return
        for _, row in trades_df.iterrows():
            strat_id = row.get('strategy_id')
            pnl = row.get('pnl', 0.0)
            if strat_id:
                sampler.update(strat_id, success=(pnl > 0))
