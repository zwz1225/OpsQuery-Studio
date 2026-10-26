# M3 categorical population candidate: local review

Date: 2026-10-25  
Policy: `bird_public_categorical_population_context_v1`  
Scope: local positive/negative tests and offline replay of the authorized schema graph. This is not a live paired experiment or a formal BIRD EX result.

## Change

The opt-in `--categorical-population` diagnostic path adds schema context when a public categorical population is explicit, unambiguous, and bound to exactly one authorized profile field. For BIRD-PG-1480, the recorded question phrase “SME customers” admits `customers.segment` and the key needed to connect it to `yearmonth.customerid`.

The candidate provides an advisory condition and a reviewed candidate equality. It does not prescribe a `WHERE` predicate, join type, SQL rewrite, or database constraint. The source review observed no null child keys or orphan rows, but the relationship remains explicitly marked as a reviewed candidate rather than a declared foreign key.

The candidate path preserves BIRD-PG-1479's existing currency field and reviewed customer key. Its original recorded `CZK` condition remains present; the new categorical policy adds no fields to that case.

## Local verification

- `tests/test_m3_condition_relations.py`: 15 tests passed. Coverage includes opt-in behavior, field/key closure, explicit entity scope, ambiguity and ownership rejection, source binding, and field/addition caps.
- `tests/test_m3_e06_pair80_bundle.py`: 3 tests passed, checking the candidate option remains compatible with the isolated E06 bundle contract.
- Offline graph audit: `evaluation/results/m3_categorical_population_graph_local_20261025_v2.json` completed. All recorded checks passed: authorized field ownership, atomic key closure, condition remains optional, join semantics remain unprescribed, 1479 remains stable, and the relationship is not labeled as an FK.
- The audit made zero model requests and opened no database connection. It replayed profile hints and source/catalog evidence recorded in the prior accepted reports; it did not perform fresh live verification or rescan full-profile uniqueness.

## Decision

The local implementation and offline graph checks are complete. The candidate is ready for a controlled isolated server comparison to determine whether the model uses the added context correctly. The offline audit does not show that generated SQL or native execution accuracy improves. Keep the candidate isolated and retain baseline evidence during that comparison.

## Evidence identity

The offline report records PostgreSQL source `bird_mini_dev_postgres_debit_card_specializing`, catalog version `326d845efc50a478187f34b539099dc53588899647bc4a1c5a7b625249080fec`, and data version `da1966f793e175cee768bf048757f41691fff18ed46cb242cddabdb041fe0450`. Source evidence hashes for capture, validation, import spec, public inputs, and development schema are recorded in the JSON report.
