1. *Modify `src/execution/base_broker.py`*
   - Add abstract method `get_capabilities(self) -> dict[str, bool]` returning a dict.
2. *Modify `src/execution/alpaca_broker.py`*
   - Implement `get_capabilities` to return `{"supports_market_orders": True, "supports_stop_limit": True, "supports_paper": True}`.
3. *Modify `src/execution/ccxt_broker.py`*
   - Implement `get_capabilities` to return `{"supports_market_orders": True, "supports_stop_limit": True, "supports_paper": True}` (or based on exchange).
4. *Create `tests/test_broker_capability.py`*
   - Implement SandboxBroker that conforms to the capability format and BaseBroker contract. Add conformance tests.
5. *Update documentation*
   - Update `docs/LIVE_DESIGN.md` and `README.md` to indicate the broker-capability is implemented.
6. *Run test*
   - Run `python -m pytest tests/test_broker_capability.py -v`
7. *Complete pre commit steps*
   - Complete pre commit steps to make sure proper testing, verifications, reviews and reflections are done.
8. *Commit and create PR*
   - Commit changes, push to `feat/broker-capability-gate`, and create a PR.
9. *Run full validation suite*
   - Run `pytest tests/ -v --cov=src`, `bandit -r src/ -lll -c bandit.toml`, `ruff check src/`.
