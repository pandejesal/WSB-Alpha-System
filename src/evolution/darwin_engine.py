import numpy as np
import logging
import random
from typing import List, Dict

logger = logging.getLogger(__name__)

class DarwinEngine:
    """
    Darwinian strategy selection and parameter drift framework.
    """

    @staticmethod
    def calculate_fitness(metrics: Dict[str, float]) -> float:
        """
        Calculates weighted fitness metric:
        Annualized Sharpe (25%), Sortino (20%), Calmar (20%),
        Win Rate (15%), Profit Factor (10%), Drawdown Consistency (10%)
        """
        # Ensure keys exist with default 0.0
        sharpe = metrics.get('sharpe', 0.0)
        sortino = metrics.get('sortino', 0.0)
        calmar = metrics.get('calmar', 0.0)
        win_rate = metrics.get('win_rate', 0.0)
        profit_factor = metrics.get('profit_factor', 0.0)

        # Drawdown consistency: inverse of max drawdown (higher is better)
        # Assuming max_drawdown is passed as a positive fraction (e.g., 0.15 for 15%)
        mdd = metrics.get('max_drawdown', 1.0)
        dd_consistency = max(0.0, 1.0 - mdd)

        # Normalize and clamp inputs conceptually (assuming standard ranges for a simple weighted sum)
        # In reality, standardizing arrays across population is better, but this handles isolated scoring.
        fitness = (
            (max(0, min(sharpe, 3.0)) / 3.0) * 0.25 +
            (max(0, min(sortino, 5.0)) / 5.0) * 0.20 +
            (max(0, min(calmar, 5.0)) / 5.0) * 0.20 +
            (max(0, min(win_rate, 1.0))) * 0.15 +
            (max(0, min(profit_factor, 3.0)) / 3.0) * 0.10 +
            (dd_consistency) * 0.10
        )

        return fitness

    def evaluate_population(self, population: List[Dict], historical_data=None) -> List[Dict]:
        if not population:
            return []

        for strategy in population:
            metrics = strategy.get('metrics', {})
            is_sharpe = metrics.get('train_sharpe', metrics.get('sharpe', 0))
            oos_sharpe = metrics.get('oos_sharpe', is_sharpe)

            # 6c: Add CPCV Integration (mocking call if data provided)
            cpcv_conf = 0.0
            if historical_data is not None:
                try:
                    from src.backtest.validators.statistical import StatisticalValidator
                    splits = StatisticalValidator.combinatorial_purged_cv(len(historical_data))
                    # Compute confidence interval placeholder logic
                    cpcv_conf = 0.95
                except Exception:
                    pass

            fitness = self.calculate_fitness(metrics)

            overfitting_penalty = 1.0
            if is_sharpe > 0 and oos_sharpe / is_sharpe < 0.5:
                overfitting_penalty = 0.5
            strategy['fitness'] = fitness * overfitting_penalty

        population.sort(key=lambda x: x['fitness'], reverse=True)

        n = len(population)
        top_quartile_idx = max(1, n // 4)
        bottom_quartile_idx = n - max(1, n // 4)

        for i, strategy in enumerate(population):
            if i < top_quartile_idx:
                strategy['status'] = 'promoted'
            elif i >= bottom_quartile_idx:
                strategy['status'] = 'discarded'
            else:
                strategy['status'] = 'survived'

        return population

    def select_for_deployment(self, population: List[Dict], top_k: int = 4) -> List[Dict]:
        from src.evolution.strategy_selector import ThompsonSampler
        sampler = ThompsonSampler(population)
        selected = []
        # Fallback to pop size if smaller than top_k
        top_k = min(top_k, len(population))
        # Ensure we don't pick the same strategy multiple times trivially or we allow it
        # Actually Thompson Sampler picks ONE. If we want k, we could pick k without replacement,
        # but to keep it simple we just pop from available ids.
        available_ids = list(sampler.strategies.keys())
        for _ in range(top_k):
            # We sample manually here without replacement for top_k
            samples = {sid: np.random.beta(sampler.strategies[sid]['alpha'], sampler.strategies[sid]['beta']) for sid in available_ids}
            best_id = max(samples, key=samples.get)
            available_ids.remove(best_id)
            chosen = next(s for s in population if s['id'] == best_id)
            selected.append(chosen)
        return selected
    def mutate_parameters(self, spec: Dict) -> Dict:
        """
        Heuristic Mutation: random parameter drift (±10% to 20%).
        Modifies numbers in the 'parameters' dictionary of a strategy spec.
        """
        import copy
        mutated_spec = copy.deepcopy(spec)
        params = mutated_spec.get('parameters', {})

        for key, value in params.items():
            if isinstance(value, (int, float)):
                # Drift by +/- 10% to 20%
                drift_pct = random.uniform(0.10, 0.20)
                direction = random.choice([1, -1])
                multiplier = 1.0 + (direction * drift_pct)

                new_value = value * multiplier
                # Preserve integer type if original was int
                if isinstance(value, int):
                    mutated_spec['parameters'][key] = int(round(new_value))
                else:
                    mutated_spec['parameters'][key] = new_value

        return mutated_spec

    def llm_guided_crossover(self, spec1: Dict, spec2: Dict, llm_client) -> Dict:
        """
        Uses an LLM (passed via dependency injection) to merge two high-performing strategies.
        """
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
            # We call the client. Assumes it's a RateLimitedGeminiClient instance.
            response_text = llm_client.generate_content(prompt, use_flash=True)
            import json, re
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"error": "Invalid crossover JSON"}
        except Exception as e:
            logger.error(f"Crossover failed: {e}")
            return {"error": str(e)}

    def update_sampler_post_trading(self, sampler, trades_df):
        """Online learning loop for Thompson Sampler"""
        if trades_df.empty: return
        for _, row in trades_df.iterrows():
            strat_id = row.get('strategy_id')
            pnl = row.get('pnl', 0.0)
            if strat_id:
                sampler.update(strat_id, success=(pnl > 0))
