# SATSA Data Dictionary (canonical records)

Conventions: `nullable` marks Optional fields; `null_policy` is how
downstream code treats nulls (null-safe features null the span, signals
gate on `min_n`); `privacy_handling` notes anonymisation; all datetimes
are timezone-aware UTC (naive values rejected).

## AuditMixin (every record)

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| ingest_ts | all | datetime UTC | no | pipeline ingest clock | reject record | — | normalised to UTC |
| source_file_hash | all | str ≥1 | no | source file bytes | reject record | — | provenance |
| record_hash | all | str ≥1 | SHA-256 of payload | computed | recompute on read | — | tamper evidence |

## Alert

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| alert_id | Alert | str ≥1 | no | CSE feed | reject record | — | primary key |
| asset_id | Alert | str ≥1 | no | CSE feed | reject record | — | joins inventory |
| title | Alert | str ≥1 | no | CSE feed | reject record | — | free text, CSV-injection stripped |
| severity_raw | Alert | str ≥1 | no | CSE feed | reject record | — | vendor string |
| severity_norm | Alert | enum CRITICAL/HIGH/MEDIUM/LOW/INFO/UNKNOWN | no | severity map | quarantine on unknown | — | normalised |
| status | Alert | enum OPEN/ACKED/TRIAGED/CLOSED/REOPENED | no (default OPEN) | CSE feed | default OPEN | — | lifecycle |
| category | Alert | str | no (default OTHER) | taxonomy map | default OTHER | — | e.g. MALWARE |
| analyst_id | Alert | 64-hex | yes | hashed triage owner | null = unassigned | salted SHA-256, never raw | — |
| detected_ts | Alert | datetime UTC | no | sensor | reject record | — | event time |
| ack_ts | Alert | datetime UTC | yes | triage | null-safe latency | — | ack latency base |
| source | Alert | str | no (default edr) | sensor | default edr | — | telemetry source |

## Asset

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| asset_id | Asset | str ≥1 | no | inventory | shadow UNKNOWN record + WARNING | — | primary key |
| hostname | Asset | str | no (default "") | inventory | default "" | internal names stay local | — |
| criticality | Asset | enum low/medium/high/… | no | inventory | default medium | — | drives expectations |
| environment | Asset | enum production/staging/development | no | inventory | reject record | — | — |
| os_family | Asset | enum linux/windows/macos | no | inventory | reject record | — | — |
| internet_facing | Asset | bool | no (default false) | inventory | default false | — | perimeter scope |
| gap_flag | Asset | bool | no (default false) | coverage engine | default false | — | expected-but-absent |

## Case

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| case_id | Case | str ≥1 | no | SOC queue | reject record | — | primary key |
| asset_id | Case | str | yes | SOC queue | null = orphan case signal | — | may be missing |
| alert_ids | Case | list[str] | no (default []) | SOC queue | empty = orphan case | — | linkage |
| severity_norm | Case | enum (as Alert) | no | triage | quarantine on unknown | — | — |
| status | Case | enum (as Alert) | no (default OPEN) | SOC queue | default OPEN | — | — |
| disposition_code | Case | enum TRUE_POSITIVE/FALSE_POSITIVE/BENIGN/DUPLICATE/INCONCLUSIVE | yes | triage | null = open case | — | batch-close grouping |
| analyst_id | Case | 64-hex | yes | hashed owner | null = unassigned | salted SHA-256 | — |
| tier | Case | enum T1/T2/T3 | no (default T1) | SOC queue | default T1 | — | escalation tracking |
| detected_ts | Case | datetime UTC | yes | SOC queue | null-safe | — | — |
| ack_ts | Case | datetime UTC | yes | triage | null-safe | — | — |
| open_ts | Case | datetime UTC | no | SOC queue | reject record | — | dwell base |
| close_ts | Case | datetime UTC | yes | triage | null = open case | — | dwell end |
| reopen_count | Case | int ≥0 | no (default 0) | SOC queue | default 0 | — | churn signal |

## Investigation

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| investigation_id | Investigation | str ≥1 | no | SOC queue | reject record | — | primary key |
| case_id | Investigation | str ≥1 | no | SOC queue | reject record | — | linkage |
| analyst_id | Investigation | 64-hex | yes | hashed owner | null-safe | salted SHA-256 | per-analyst text stats |
| detected_ts | Investigation | datetime UTC | yes | SOC queue | null-safe | — | — |
| ack_ts | Investigation | datetime UTC | yes | triage | null-safe | — | — |
| triage_start_ts | Investigation | datetime UTC | yes | triage | null-safe | — | triage duration base |
| triage_end_ts | Investigation | datetime UTC | yes | triage | null-safe | — | triage duration end |
| close_ts | Investigation | datetime UTC | yes | triage | null-safe | — | — |
| notes | Investigation | str | no (default "") | analyst | blank = placeholder ratio | PII scrubbed by guardrails | truncated >4096 chars for embedding |
| steps | Investigation | list[InvestigationStep] | no (default []) | analyst tool | default [] | — | nested actions |

## InvestigationStep (nested)

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| step_id | InvestigationStep | str ≥1 | no | analyst tool | reject step | — | — |
| timestamp | InvestigationStep | datetime UTC | no | analyst tool | reject step | — | — |
| action | InvestigationStep | str ≥1 | no | analyst tool | reject step | — | — |
| notes | InvestigationStep | str | no (default "") | analyst | default "" | PII scrubbed | — |

## Escalation

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| escalation_id | Escalation | str ≥1 | no | SOC queue | reject record | — | primary key |
| case_id | Escalation | str ≥1 | no | SOC queue | reject record | — | linkage |
| from_tier | Escalation | enum T1/T2/T3 | no (default T1) | SOC queue | default T1 | — | — |
| to_tier | Escalation | enum T1/T2/T3 | no (default T2) | SOC queue | default T2 | — | — |
| escalated_ts | Escalation | datetime UTC | yes | SOC queue | null accepted_ts = nowhere signal | — | — |

## Telemetry

| field_name | model | type | nullable | source | null_policy | privacy_handling | notes |
|---|---|---|---|---|---|---|---|
| telemetry_id | Telemetry | str ≥1 | no | collector | reject record | — | primary key |
| asset_id | Telemetry | str ≥1 | no | collector | reject record | — | coverage join |
| source | Telemetry | str ≥1 | no | collector | reject record | — | edr/firewall/ids/auth/sysmon |
| observed_ts | Telemetry | datetime UTC | no | collector | reject record | — | silence streaks |
