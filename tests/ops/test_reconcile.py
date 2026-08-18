from unittest.mock import patch

from scripts.reconcile import run_reconciliation


def test_reconciliation_clean_mocked():
    # Since the script hardcodes paths, we mock the file reading directly
    plan_data = '{"targets": [{"ticker": "AAPL"}]}'
    fills_data = '[{"ticker": "AAPL"}]'

    def mock_open_impl(path, mode="r"):
        from unittest.mock import mock_open
        if "plan.json" in path:
            return mock_open(read_data=plan_data)()
        elif "fills.json" in path:
            return mock_open(read_data=fills_data)()
        return mock_open()()

    with patch("scripts.reconcile.os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=mock_open_impl), \
         patch("scripts.reconcile.AlertManager") as mock_am, \
         patch("scripts.reconcile.write_artifact") as mock_write:

        run_reconciliation()

        mock_am.return_value.send.assert_not_called()
        call_args = mock_write.call_args[0][1]
        assert call_args["status"] == "clean"
        assert len(call_args["mismatches"]) == 0

def test_reconciliation_mismatch_mocked():
    # Plan has AAPL, but fills has MSFT
    plan_data = '{"targets": [{"ticker": "AAPL"}]}'
    fills_data = '[{"ticker": "MSFT"}]'

    def mock_open_impl(path, mode="r"):
        from unittest.mock import mock_open
        if "plan.json" in path:
            return mock_open(read_data=plan_data)()
        elif "fills.json" in path:
            return mock_open(read_data=fills_data)()
        return mock_open()()

    with patch("scripts.reconcile.os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=mock_open_impl), \
         patch("scripts.reconcile.AlertManager") as mock_am, \
         patch("scripts.reconcile.write_artifact") as mock_write:

        run_reconciliation()

        mock_am.return_value.send.assert_called_once()
        assert "CRITICAL" in mock_am.return_value.send.call_args[0]

        call_args = mock_write.call_args[0][1]
        assert call_args["status"] == "mismatch"
        assert len(call_args["mismatches"]) == 2 # AAPL missing, MSFT unplanned
