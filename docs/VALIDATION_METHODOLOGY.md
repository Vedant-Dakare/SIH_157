# SATSA Validation Methodology (for NCIIPC review)

## 1. Label sources and their limitations

- **(a) Synthetic ground truth** (`data/synthetic/ground_truth.parquet`,
  default): 10 planted issues across 10 synthetic CSEs. Strengths:
  deterministic, covers every scenario. Limitations: planted by the same
  team that built the generator (optimistic recall); note wording
  ("planted") is a synthetic artefact, never present in real data (R1).
- **(b) Expert review labels**: any parquet with the same schema —
  `entity_id, signal_id|issue_type, expected_flag|severity|confidence,
  rationale|note, reviewer_id, reviewed_at` (one-line `--labels` change,
  no code changes per A1). Limitations: reviewer disagreement, sampling
  noise, and coverage gaps in manual review itself.

## 2. Sampling strategy

Expert Review Simulation Protocol: stratified sample of 20 cases per
entity × 10 entities = 200 cases; strata by severity tier —
50% CRITICAL/HIGH, 30% MEDIUM, 20% LOW. Rationale: supervisory risk
concentrates in high-severity triage, so the sample oversamples it while
keeping medium/low representation for calibration. At ~10 min per case
the protocol costs ≈ 33 reviewer-hours per round.

## 3. Metrics: definitions and supervisory relevance

- **precision@k (k = 5, 10, 20)**: share of the top-k ranked findings that
  match labels. Matters because reviewers work the queue top-down.
- **recall_by_scenario**: per-scenario hit rate on planted/expected issues.
  S1 (healthy) scores 1.0 vacuously when nothing fires.
- **F1 by family**: precision/recall balance per signal family
  (execution_gap, negative_space, composite).
- **Cohen's kappa**: chance-adjusted agreement with labels in [-1, 1].
  Synthetic labels are rater A, SAT-SA rater B (R2: two-rater minimum met
  by construction, not by independent experts — real reviews need ≥ 2
  human raters for a publishable kappa).
- **Krippendorff's alpha (nominal)**: second agreement view, robust to
  skewed marginals.
- **false_positive_analysis**: every flag on the S1 healthy control, each
  a candidate threshold or generator defect.
- **coverage_rate**: share of expert-found issues SAT-SA also finds.
- **efficiency_gain**: reviewer-hours saved per finding vs the 200-case
  manual protocol. **time_to_finding**: pipeline seconds vs manual seconds.

## 4. "Comparable to or better than manual sampling" (proposed, A2)

Provisional acceptance bar, pending NCIIPC confirmation: recall ≥ 0.80 on
HIGH/CRITICAL scenarios, precision@10 ≥ 0.70, Cohen's kappa ≥ 0.60.

## 5. Known limitations

- Synthetic labels flatter real-world ambiguity; S10 (partial feed) recall
  is expected to be low because records are genuinely missing (R3) —
  treat as expected behaviour, not failure.
- Extra SAT-SA flags outside the 10 labelled SIG_* ids (e.g. EG-007,
  NS-011) are invisible to kappa but visible in precision and the
  disagreement report.

## 6. Running validation on real NCIIPC data

1. Reviewers complete `docs/expert_review_rubric_template.csv` per the
   rubric (`docs/EXPERT_REVIEW_RUBRIC.md`).
2. Convert rows to the ExpertLabel parquet schema (same columns as the
   synthetic file).
3. Run `python -m satsa.validation.benchmark --labels <parquet>
   --run-id <id>`; read HTML + JSON in `data/curated/validation/`.
4. Compare against §4 thresholds; adjudicate disagreements via
   `expert_agreement` (feedback → `adjudications.jsonl`).

## 7. Adjudication process

Every disagreement ships its full EvidenceBundle. A reviewer records
`SAT_SA_CORRECT | EXPERT_CORRECT | BOTH_WRONG | INCONCLUSIVE` plus an
optional threshold suggestion; a human — never the pipeline — edits
`thresholds.yaml` (ADR-009).
