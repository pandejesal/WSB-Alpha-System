import json
import logging
import ast
from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, END
from src.utils.gemini_client import RateLimitedGeminiClient
from src.utils.config import config

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    research_topic: str
    discovered_ideas: str
    strategy_specification: dict
    generated_code: str
    backtest_metrics: dict
    validation_passed: bool
    feedback: str
    reflection_count: int
    regime: str
    regime_confidence: float
    adjusted_parameters: dict

class ResearchWorkflow:
    def __init__(self):
        try:
            api_key = config.api_keys.gemini_api_key.get_secret_value()
        except AttributeError:
            api_key = config.api_keys.gemini_api_key

        self.llm = RateLimitedGeminiClient(api_key=api_key)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(GraphState)

        workflow.add_node("research", self.research_node)
        workflow.add_node("regime_detection", self.regime_detection_node)
        workflow.add_node("specification", self.specification_node)
        workflow.add_node("code_generation", self.code_generation_node)
        workflow.add_node("reflection", self.reflection_node)

        workflow.set_entry_point("research")
        workflow.add_edge("research", "regime_detection")
        workflow.add_edge("regime_detection", "specification")
        workflow.add_edge("specification", "code_generation")
        workflow.add_edge("code_generation", "reflection")

        workflow.add_conditional_edges(
            "reflection",
            self.route_reflection,
            {
                "end": END,
                "retry": "specification"
            }
        )

        return workflow.compile()

    def research_node(self, state: GraphState) -> dict:
        logger.info(f"--- RESEARCHING: {state['research_topic']} ---")
        prompt = f"Conduct quantitative research on: {state['research_topic']}. Find raw trading alpha ideas or market inefficiencies."
        ideas = self.llm.generate_content(prompt, use_flash=False, search_grounding=True)
        return {"discovered_ideas": ideas, "reflection_count": state.get("reflection_count", 0)}

    def regime_detection_node(self, state: GraphState) -> dict:
        try:
            from src.alpha.indicators import compute_indicators
            from src.risk.position_sizer import RegimeDetector
            import yfinance as yf
            import pandas as pd

            spy = yf.download("SPY", period="60d", progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)

            if spy.empty:
                return {"regime": "normal", "regime_confidence": 0.5, "adjusted_parameters": {}}

            spy = spy.reset_index()
            cols = spy.columns.tolist()
            rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date']}
            spy.rename(columns=rename_map, inplace=True)

            ind = compute_indicators(spy)
            if ind is None or 'GK_Vol' not in ind.columns or ind.empty:
                return {"regime": "normal", "regime_confidence": 0.5, "adjusted_parameters": {}}

            current_gk_vol = ind['GK_Vol'].iloc[-1]
            regime = RegimeDetector.detect_regime(current_gk_vol)

            regime_params = {
                "low_volatility": {"rsi_threshold": 35, "bb_width": 1.5, "holding_days": 7},
                "normal": {"rsi_threshold": 40, "bb_width": 2.0, "holding_days": 5},
                "high_volatility": {"rsi_threshold": 45, "bb_width": 2.5, "holding_days": 3}
            }

            return {
                "regime": regime,
                "regime_confidence": min(1.0, current_gk_vol / 0.5),
                "adjusted_parameters": regime_params.get(regime, regime_params["normal"])
            }
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return {"regime": "normal", "regime_confidence": 0.5, "adjusted_parameters": {}}

    def specification_node(self, state: GraphState) -> dict:
        logger.info("--- GENERATING SPECIFICATION ---")
        feedback = state.get('feedback', '')
        regime = state.get('regime', 'normal')
        adjusted_params = state.get('adjusted_parameters', {})

        prompt = f"""
        Parse the following research ideas into a strict Pydantic JSON Strategy Specification.
        Research Ideas: {state.get('discovered_ideas', '')}
        Previous Feedback: {feedback}
        Current Market Regime: {regime}
        Regime-Adjusted Parameters: {json.dumps(adjusted_params)}

        Output ONLY raw valid JSON matching this schema:
        {{
            "strategy_name": "string",
            "indicators": ["string", "string"],
            "entry_logic": "string",
            "exit_logic": "string",
            "parameters": {{"param1": float}}
        }}
        """

        spec_text = self.llm.generate_content(prompt, use_flash=True)
        try:
            import re
            match = re.search(r'\{.*\}', spec_text, re.DOTALL)
            if match:
                spec_json = json.loads(match.group(0))
            else:
                spec_json = {"error": "Invalid JSON format generated"}
        except Exception as e:
            spec_json = {"error": str(e)}

        return {"strategy_specification": spec_json}

    def code_generation_node(self, state: GraphState) -> dict:
        logger.info("--- GENERATING CODE ---")
        spec = state.get("strategy_specification", {})

        prompt = f"Generate a Python function `def generate_signals(df):` based on this specification: {json.dumps(spec)}. Output ONLY python code."
        code = self.llm.generate_content(prompt, use_flash=True)
        code = code.replace("```python", "").replace("```", "").strip()

        try:
            import tempfile
            import subprocess
            from RestrictedPython import compile_restricted, safe_builtins

            try:
                byte_code = compile_restricted(code, '<inline>', 'exec')
            except Exception as e:
                raise ValueError(f"RestrictedPython failed to compile code safely: {e}")

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
                tf.write(code)
                temp_name = tf.name

            try:
                result = subprocess.run(
                    ['bandit', '-r', temp_name, '-f', 'json'],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    import json as json_lib
                    try:
                        bandit_out = json_lib.loads(result.stdout)
                        if bandit_out.get('metrics', {}).get('_totals', {}).get('SEVERITY.HIGH', 0) > 0:
                            raise ValueError(f"Bandit found HIGH severity security issues.")
                    except json_lib.JSONDecodeError:
                        raise ValueError(f"Bandit execution returned non-zero code but output was unparsable.")
            finally:
                import os
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

            sanitized_code = code
        except Exception as e:
            logger.error(f"AST/Static Analysis failed: {e}")
            sanitized_code = f"# Error generating safe code: {e}"

        return {"generated_code": sanitized_code}

    def reflection_node(self, state: GraphState) -> dict:
        from src.backtest.run_historic_backtest import run_backtest

        generated_code = state.get("generated_code", "")
        if not generated_code or generated_code.startswith("# Error"):
            return {"feedback": "Code generation failed", "validation_passed": False, "reflection_count": state.get("reflection_count", 0) + 1}

        try:
            if "def generate_signals" in generated_code:
                local_env = {}
                exec(generated_code, {"__builtins__": {}}, local_env)

            trades = run_backtest()
            if trades.empty:
                return {"feedback": "No trades generated", "validation_passed": False, "reflection_count": state.get("reflection_count", 0) + 1}

            total_return = trades['return'].sum() if 'return' in trades.columns else 0
            std_ret = trades['return'].std() if 'return' in trades.columns else 1e-10
            sharpe = (trades['return'].mean() / (std_ret + 1e-10)) if 'return' in trades.columns else 0

            if 'return' in trades.columns:
                cum_ret = trades['return'].cumsum()
                max_dd = (cum_ret.cummax() - cum_ret).max()
            else:
                max_dd = 1.0

            metrics = {
                "total_return": float(total_return),
                "sharpe": float(sharpe),
                "max_drawdown": float(max_dd)
            }

            passed = sharpe > 1.0 and total_return > 0 and max_dd < 0.20

            return {
                "backtest_metrics": metrics,
                "validation_passed": passed,
                "feedback": f"Sharpe: {sharpe:.2f}, Return: {total_return*100:.1f}%, MaxDD: {max_dd*100:.1f}%",
                "reflection_count": state.get("reflection_count", 0) + 1 if not passed else state.get("reflection_count", 0)
            }
        except Exception as e:
            return {"feedback": f"Backtest failed: {e}", "validation_passed": False, "reflection_count": state.get("reflection_count", 0) + 1}

    def route_reflection(self, state: GraphState) -> str:
        if state.get("validation_passed", False):
            return "end"
        if state.get("reflection_count", 0) >= 3:
            logger.warning("Max reflection limit reached. Ending.")
            return "end"
        return "retry"

    def execute(self, topic: str):
        initial_state = {
            "research_topic": topic,
            "discovered_ideas": "",
            "strategy_specification": {},
            "generated_code": "",
            "backtest_metrics": {},
            "validation_passed": False,
            "feedback": "",
            "reflection_count": 0,
            "regime": "normal",
            "regime_confidence": 0.5,
            "adjusted_parameters": {}
        }
        return self.graph.invoke(initial_state)
