# Expert Review Rubric (simulation protocol + real-review guide)

## 1. Case selection criteria

Stratified sample: 20 cases per entity × 10 entities = 200 cases;
50% CRITICAL/HIGH, 30% MEDIUM, 20% LOW severity. Sample within strata by
fixed-seed random draw so rounds are reproducible. Replace any case that
is a duplicate of another sampled case (record the replacement).

## 2. Assessment dimensions (per case, present/absent + 1-line note)

1. **Adequate investigation evidence** — notes, steps and artefacts
   support the disposition.
2. **Escalation where warranted** — CRITICAL/HIGH cases show timely
   tier escalation; bypasses are justified in writing.
3. **Root cause addressed** — recurrence risk (reopens, duplicates)
   is dispositioned, not just closed.
4. **Telemetry coverage adequate** — expected sources for the asset's
   criticality/environment are present during the window.

## 3. Scoring guide

Each dimension: 1 (present) / 0 (absent) / NA (not applicable, with
reason). A case passes when no applicable dimension scores 0. Record
overall `expected_flag` semantics: True = issue present (any 0),
False = no issue. Confidence 0–1 reflects reviewer certainty.

## 4. Output format (maps directly to the ExpertLabel schema)

Columns: `entity_id, signal_id, expected_flag, confidence, reviewer_id,
reviewed_at, rationale`. `signal_id` uses the SIG_* vocabulary
(`docs/expert_review_rubric_template.csv` has one example row per signal).
`reviewer_id` must be a hashed identifier, never a name.

## 5. Example completed rows

See the header + examples in `docs/expert_review_rubric_template.csv`.

## 6. Inter-rater reliability guidance

Double-review ≥ 20% of cases with independent reviewers; compute Cohen's
kappa on the overlap (target ≥ 0.60 before trusting single-review labels).
Adjudicate disagreements by majority or senior-reviewer verdict and log
them in `adjudications.jsonl` format.
