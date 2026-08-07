import os
import json
from unittest.mock import patch
import pytest
from scripts.run_research import main

def test_run_research_end_to_end(tmp_path):
    # Setup mock universe
    universe_path = tmp_path / "universe.json"
    universe_data = {"tickers": ["AAPL", "MSFT"]}
    universe_path.write_text(json.dumps(universe_data))

    # Mock output dir
    docs_data_dir = tmp_path / "docs" / "data"

    with patch("builtins.open") as mock_open_builtins, \
         patch("scripts.run_research.os.path.exists") as mock_exists, \
         patch("scripts.run_research.json.load") as mock_json_load, \
         patch("scripts.run_research.FredMacroProvider") as MockFred, \
         patch("scripts.run_research.fetch_agentic_headlines") as mock_fetch, \
         patch("scripts.run_research.score_text") as mock_score_text, \
         patch("scripts.run_research.DebateEngine") as MockDebateEngine:

        # Make os.path.exists return True for universe.json
        def mocked_exists(path):
            if "universe.json" in path:
                return True
            return False
        mock_exists.side_effect = mocked_exists

        # Mock json load
        def mocked_json_load(*args, **kwargs):
            if "dummy.json" in args[0].name:
                 return {}
            # for universe
            return {"tickers": ["AAPL", "MSFT"]}

        mock_json_load.side_effect = mocked_json_load

        mock_fred_instance = MockFred.return_value
        mock_fred_instance.regime_multiplier.return_value = 1.2

        mock_fetch.return_value = [
            {"headline": "Mock headline 1", "source": "Test", "url": "", "timestamp": ""},
            {"headline": "Mock headline 2", "source": "Test", "url": "", "timestamp": ""}
        ]
        mock_score_text.return_value = {"net_score": 0.5, "classification": "positive"}

        mock_debate_instance = MockDebateEngine.return_value
        mock_debate_instance.run_debate.return_value = {
            "score": 0.5,
            "stance": "bullish",
            "reasoning": ["Bull: Looks good"]
        }

        # Intercept the writing to the output file to write to our tmp path instead
        # We need to capture the *actual* built-in open function before patching it,
        # but since we already patched it, we should use the builtin module directly without dict lookup.
        import builtins as __b__
        original_open = getattr(__b__, 'open') # if not mocked yet
        if hasattr(original_open, "side_effect"):
             # If it's a mock, we need the original from python core
             import io
             original_open = io.open

        def mocked_open(*args, **kwargs):
            if isinstance(args[0], str) or hasattr(args[0], "__fspath__"):
                path_str = str(args[0])
                if "research_sentiment.json" in path_str:
                    return original_open(docs_data_dir / "research_sentiment.json", *args[1:], **kwargs)
                elif "universe.json" in path_str:
                    return original_open(universe_path, *args[1:], **kwargs)
                elif "dummy.json" in path_str:
                    return original_open(tmp_path / "dummy.json", "w", *args[1:], **kwargs) # ensure dummy can be opened
            return original_open(*args, **kwargs)

        mock_open_builtins.side_effect = mocked_open

        # Ensure the directory exists so open doesn't fail
        docs_data_dir.mkdir(parents=True, exist_ok=True)

        main()

    # Assertions outside the patch block
    output_file = docs_data_dir / "research_sentiment.json"
    assert output_file.exists(), "The research_sentiment.json file was not created."

    with open(output_file, "r") as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["stance"] == "BULLISH"
    # 0.5 base score * 1.2 regime multiplier = 0.6
    assert data[0]["score"] == 0.6
