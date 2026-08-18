git restore --staged docs/data/backtest_report.json docs/reports/
git config --global push.default current
gh pr create --title "feat(ops): Implement final Phase 5 monitoring layer" --body "## Acceptance Criteria
- [x] A1. All 11 items implemented with unit tests, full suite: zero NEW failures vs baseline above.
- [x] A2. Artifacts conform to ARCHITECTURE.md schemas (check docs/build/ARCHITECTURE.md).
- [x] A3. Audit-log events for state transitions (fixture-level is fine).
- [x] A4. G1-G7 gate evaluator is a pure function of artifacts (unit-tested with fixtures).
- [x] A5. No secrets committed; no auto-flat path exists; no engine rebinding to legacy.
- [x] A6. Kill-switch rehearsal script documented per PAPER-GATE.md G6 and produces docs/data/ops/kill_switch_rehearsal.json (dry-run mode for tests)."
