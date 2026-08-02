import json
import logging
import ast
from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, END
from src.utils.gemini_client import RateLimitedGeminiClient
from src.utils.config import config

logger = logging.getLogger(__name__)

# State definition
class GraphState(TypedDict):
    research_topic: str
    discovered_ideas: str
    strategy_specification: dict
    generated_code: str
    backtest_metrics: dict
    validation_passed: bool
    feedback: str
    reflection_count: int

class ResearchWorkflow:
    def __init__(self):
        # We need the key from the loaded config
        # config.api_keys is our Stub in tests, but in reality it's the Pydantic object
        try:
            api_key = config.api_keys.gemini_api_key.get_secret_value()
        except AttributeError:
            api_key = config.api_keys.gemini_api_key

        self.llm = RateLimitedGeminiClient(api_key=api_key)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(GraphState)

        workflow.add_node("research", self.research_node)
        workflow.add_node("specification", self.specification_node)
        workflow.add_node("code_generation", self.code_generation_node)
        workflow.add_node("reflection", self.reflection_node)

        workflow.set_entry_point("research")

        workflow.add_edge("research", "specification")
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

        # Use Flash Lite with Search Grounding
        ideas = self.llm.generate_content(prompt, use_flash=False, search_grounding=True)
        return {"discovered_ideas": ideas, "reflection_count": state.get("reflection_count", 0)}

    def specification_node(self, state: GraphState) -> dict:
        logger.info("--- GENERATING SPECIFICATION ---")

        feedback = state.get('feedback', '')
        prompt = f"""
        Parse the following research ideas into a strict Pydantic JSON Strategy Specification.
        Research Ideas: {state.get('discovered_ideas', '')}
        Previous Feedback (if any): {feedback}

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

        # Cleanup markdown
        code = code.replace("```python", "").replace("```", "").strip()

        # AST Sanitization and Static Analysis
        try:
            import tempfile
            import subprocess
            from RestrictedPython import compile_restricted, safe_builtins

            # 1. RestrictedPython check
            try:
                byte_code = compile_restricted(code, '<inline>', 'exec')
            except Exception as e:
                raise ValueError(f"RestrictedPython failed to compile code safely: {e}")

            # 2. Bandit static analysis check
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
                tf.write(code)
                temp_name = tf.name

            try:
                # Run bandit on the generated file
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
        logger.info("--- REFLECTING ON RESULTS ---")

        # In a real environment, we'd run the backtest here and evaluate metrics.
        # Since this is a standalone workflow orchestrator, we simulate the validation.
        # If the state doesn't have passed metrics, we fail it to test the loop.

        metrics = state.get("backtest_metrics", {})
        passed = state.get("validation_passed", False)

        if not passed:
            feedback = "Backtest failed or returned negative profit. Adjust parameters to reduce risk."
            return {"feedback": feedback, "reflection_count": state.get("reflection_count", 0) + 1}
        else:
            return {"feedback": "Success", "reflection_count": state.get("reflection_count", 0)}

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
            "reflection_count": 0
        }
        return self.graph.invoke(initial_state)
