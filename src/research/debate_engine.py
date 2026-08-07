import logging
from typing import Dict, Any, List
from src.research.browser_scraper import fetch_headlines, score_text

logger = logging.getLogger(__name__)

class DebateEngine:
    """
    Runs a 3-agent programmatic debate simulation (bull, bear, neutral) on a ticker.
    Utilizes fetch_headlines and score_text to form stances.
    """
    def __init__(self):
        pass

    def run_debate(self, ticker: str) -> Dict[str, Any]:
        headlines = fetch_headlines(ticker)

        # If fetch fails or has no data, agents still run but with low confidence
        base_score = score_text(headlines)

        agents_output = []

        # Bull Agent logic
        try:
            bull_output = self._simulate_bull_agent(ticker, headlines, base_score)
            if bull_output:
                agents_output.append(bull_output)
        except Exception as e:
            logger.error(f"Error executing Bull Agent: {e}")

        # Bear Agent logic
        try:
            bear_output = self._simulate_bear_agent(ticker, headlines, base_score)
            if bear_output:
                agents_output.append(bear_output)
        except Exception as e:
            logger.error(f"Error executing Bear Agent: {e}")

        # Neutral Agent logic
        try:
            neutral_output = self._simulate_neutral_agent(ticker, headlines, base_score)
            if neutral_output:
                agents_output.append(neutral_output)
        except Exception as e:
            logger.error(f"Error executing Neutral Agent: {e}")

        # Compute Consensus Q-Score
        # Weighted by confidence. Neutral dampens (has 0 score but adds to total confidence denominator).
        total_confidence = sum(a['confidence'] for a in agents_output)

        if total_confidence == 0:
            q_score = 0.0
            overall_stance = "neutral"
        else:
            weighted_score = sum(self._stance_to_val(a['stance']) * a['confidence'] for a in agents_output)
            q_score = weighted_score / total_confidence

            if q_score > 0.33:
                overall_stance = "bullish"
            elif q_score < -0.33:
                overall_stance = "bearish"
            else:
                overall_stance = "neutral"

        reasoning = [f"{a['role'].capitalize()} Agent: {a['reasoning']}" for a in agents_output]

        return {
            "ticker": ticker,
            "score": round(q_score, 4),
            "stance": overall_stance,
            "agents": agents_output,
            "reasoning": reasoning
        }

    def _stance_to_val(self, stance: str) -> float:
        if stance == "bullish":
            return 1.0
        elif stance == "bearish":
            return -1.0
        return 0.0

    def _simulate_bull_agent(self, ticker: str, headlines: List[str], base_score: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Bull looks for positive ratio
            pos_ratio = base_score.get("positive_ratio", 0.0)
            if not headlines:
                return {
                    "role": "bull",
                    "stance": "neutral",
                    "confidence": 0.1,
                    "reasoning": f"No recent headlines found for {ticker}, keeping a neutral stance."
                }

            confidence = min(0.5 + pos_ratio, 1.0)
            if base_score.get("classification") == "positive":
                stance = "bullish"
                reasoning = f"Positive sentiment ratio ({pos_ratio:.2f}) indicates upward momentum."
            else:
                stance = "neutral"
                reasoning = "Not enough positive sentiment to maintain a strong bullish outlook."
                confidence *= 0.5

            return {
                "role": "bull",
                "stance": stance,
                "confidence": round(confidence, 2),
                "reasoning": reasoning
            }
        except Exception as e:
            logger.error(f"Bull agent failed: {e}")
            return None

    def _simulate_bear_agent(self, ticker: str, headlines: List[str], base_score: Dict[str, Any]) -> Dict[str, Any]:
        try:
            neg_ratio = base_score.get("negative_ratio", 0.0)
            if not headlines:
                return {
                    "role": "bear",
                    "stance": "neutral",
                    "confidence": 0.1,
                    "reasoning": f"Lack of data for {ticker} prevents a strong bearish thesis."
                }

            confidence = min(0.5 + neg_ratio, 1.0)
            if base_score.get("classification") == "negative":
                stance = "bearish"
                reasoning = f"Negative sentiment ratio ({neg_ratio:.2f}) points to potential downside."
            else:
                stance = "neutral"
                reasoning = "Insufficient negative indicators to form a strong bearish position."
                confidence *= 0.5

            return {
                "role": "bear",
                "stance": stance,
                "confidence": round(confidence, 2),
                "reasoning": reasoning
            }
        except Exception as e:
            logger.error(f"Bear agent failed: {e}")
            return None

    def _simulate_neutral_agent(self, ticker: str, headlines: List[str], base_score: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not headlines:
                return {
                    "role": "neutral",
                    "stance": "neutral",
                    "confidence": 0.9,
                    "reasoning": f"Complete lack of market news for {ticker} justifies strict neutrality."
                }

            net_score = abs(base_score.get("net_score", 0.0))

            # Neutral agent confidence is inversely proportional to the absolute net score
            confidence = max(0.1, 1.0 - (net_score * 2))

            if confidence > 0.5:
                stance = "neutral"
                reasoning = "Balanced market sentiment suggests no clear directional advantage."
            else:
                stance = "neutral"
                reasoning = "Volatility is present, but overall signals are mixed."

            return {
                "role": "neutral",
                "stance": stance,
                "confidence": round(confidence, 2),
                "reasoning": reasoning
            }
        except Exception as e:
            logger.error(f"Neutral agent failed: {e}")
            return None
