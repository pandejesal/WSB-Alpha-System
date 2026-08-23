# Review Checklist (Layer 3)

Score every item with numbers cited from results.json. Any FAIL on items 1-6
forces overall FAIL. Items 7-9 are flags requiring explicit justification.

1. [ ] Pre-registration intact: brief approved by user BEFORE backtest ran; spec
       matches the brief (no post-hoc edits).
2. [ ] In-sample: p-value <= 0.05.
3. [ ] Combinatorial purged CV passed.
4. [ ] Walk-forward: positive OOS across folds; no single fold carries result
       (check fold dispersion).
5. [ ] Permutation test survived at declared NUM_PERMUTATIONS.
6. [ ] DSR ledger entry positive.
7. [ ] Parameter count justified vs sample size (state ratio).
8. [ ] No universe/window changes after results were seen.
9. [ ] Reported variant == declared variant (no cherry-picking).

Verdict rules:
- All of 1-6 pass and no unjustified flags 7-9 -> PASS (pending operator approval).
- Any of 1-6 fail -> FAIL.
- Flags without justification -> REVISE with named fixes.

A FAIL is a successful pipeline run. Do not soften verdicts.
