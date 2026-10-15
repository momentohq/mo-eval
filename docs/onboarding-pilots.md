# Onboarding pilot worksheet

Use one real task to discover the smallest integration needed for an agent to work on mo-eval. Preserve the [product experience](../README.md) while testing the boundaries in the [service design](service-design.md). This is a collaborative worksheet, not a completed fixture or a launch plan.

Status: planning, 2026-10-15. Both pilots need agent-owner and domain-reviewer input. No complete reviewed task environment or private oracle is asserted here. Keep raw customer logs, credentials, private identifiers and oracle answers outside this public repository; record access-controlled artifact references and hashes where permitted.

## First milestone

One representative task goes through the actual agent host using a scripted model/session, a frozen environment, trusted capture and an offline verifier. It produces an accepted candidate and an assessable result without model spend. Scripted conformance proves wiring and checks, not autonomous agent quality.

Then add a counterfactual task and, where practical, a second client. Record precisely which data/configuration or adapter changed. Agree a separately authorized model trial only after the task and checks are reviewed.

## Choose owners and placement

Fill these in before implementation; role names do not assign someone work.

| Responsibility | On-call pilot | Anti-piracy pilot |
|---|---|---|
| Agent/driver owner | To assign | To assign |
| Task/environment author | To assign | To assign |
| Domain/oracle reviewer | To assign | To assign |
| Capture/verifier integration owner | To assign | To assign |
| Agent/services/verifier placement | Choose local conformance versus hosted milestone | Choose local conformance versus hosted milestone |
| Private artifact location and access | To agree | To agree |
| Implementation tracking issue | To scope and link | To scope and link |
| First task and review date | To choose | To choose |

## On-call triage

Goal: help a responder understand a supplied incident and choose a safe next diagnostic or proposed action. The initial task does not execute repairs.

| Component | First task definition | Input or gap to resolve |
|---|---|---|
| Agent | Actual triage host, prompts, tool policy and effective model/round settings | Pin build/runtime and dependency closure |
| Driver | Invoke host with injected services and fresh state | Confirm supported seam and scripted session entry; avoid production credential/bootstrap path |
| Public task | Status/urgency, supported explanation, uncertainty and safe next step with preconditions/verification | Domain owner reviews criteria and escalation policy |
| Environment | Exact trigger/date, incident records, scope/topology/configuration, metrics/log windows and public runbooks | Choose smallest recoverable incident; document absent history and valid queries |
| Candidate | Structured report, rendered projection, proposal records and evidence references | Confirm output schema and capture first/final submissions |
| Private oracle | Reviewed facts, acceptable explanations/actions, uncertainty and disagreement | Keep later diagnosis out of agent-visible inputs; allow equivalent safe steps |
| Verifier | Completion, support, resource scope, time leakage and next-step checks | Syntax/profile validation alone cannot establish action safety |
| Metrics | Assessable/supported reports, wrong-scope proposals, completion and report latency | Separate agent execution, manual launch delay and observational human resolution time |

Immediate next step: agent owner demonstrates the host's injectable launch path; environment author and incident owner select a task with recoverable incident-time configuration. The integration owner then records exactly what evidence the host emits and what requires independent capture.

## Anti-piracy triage

Goal: investigate a supplied entity/time window and produce a supported verdict, uncertainty and permissible next investigative step. The initial task does not change access control. Discovery across all traffic without a supplied entity is a different task.

| Component | First task definition | Input or gap to resolve |
|---|---|---|
| Agent | Actual entity-triage host, prompts and tool policy | Obtain package, tool schemas, launch contract and output schema |
| Driver | Bind frozen traffic/entity/log reads and verdict submission | Identify injection seam and scripted launch/capture hooks |
| Public task | Identify supported patterns, cite evidence, express confidence/uncertainty | Do not require a particular verdict from an illustrative run |
| Environment | Frozen traffic/session records, identity mapping, limits and policy for exact window | Reconcile aggregates with raw rows; preserve truncation and missing-data semantics |
| Candidate | Verdict, claims/citations, unresolved questions and proposed next step | Capture submission independently of candidate-written logs |
| Private oracle | Reviewed supported facts, authorized automation and acceptable conclusions | Access logs alone may not establish malicious intent |
| Verifier | Entity/window scope, evidence support, uncertainty and allowed action | Explicitly accept justified unknowns |
| Metrics | Support, abstention, unnecessary-action rate, cost and latency | Precision/recall only with adjudicated labels and fixed threshold/abstention policy |

Immediate next step: agent owner supplies its host/tool contract and a private candidate recording; domain reviewer selects a legitimate-automation control and decides what conclusions the available evidence can support. Do not treat the earlier sample trajectory as confirmed piracy or a complete dataset.

## Shared conformance checklist

Mark a check complete only after running the real producer/guard and retaining its output. Missing fixture coverage must be explicit, not interpreted as an empty answer or evidence of absence.

- [ ] Pin task, agent configuration, environment inputs, driver, verifier and parser versions.
- [ ] Actual host starts from fresh state and reaches an accepted supported candidate with scripted inputs.
- [ ] Different valid query orders return consistent facts; unsupported queries are explicitly classified.
- [ ] Opening host reads and model-driven tool requests/results are captured with arguments and IDs.
- [ ] Wrong entity/account, invented evidence/proposal, missing trace and absent candidate fail for the expected reason.
- [ ] Later configuration/diagnosis does not leak into historical observations.
- [ ] Good, bad and ambiguous outputs receive reviewed assessments; faults are separate from agent failure.
- [ ] Cancellation stops child processes, preserves partial evidence and leaves no writable state for the next task.
- [ ] Reassessment adds only an assessment; original attempt IDs and sealed evidence remain unchanged.
- [ ] Report includes planned/assessable/missing counts, criterion outcomes and capture/usage coverage.
- [ ] Change one task's data and one agent configuration without rewriting driver, backend or metric reducers where contracts remain compatible.

The no-spend test has no model cost or realistic model latency measurement. Later metered trials must retain all-attempt usage, judge cost separately, timing boundaries and incomplete-cost flags.

## Track integration work

For each gap, add an issue URL, owner, concrete input and acceptance artifact before implementing it. A small task-data/configuration change should not become a new framework. A new shared abstraction should name the repeated coupling it removes.

| Gap | Smallest useful deliverable | Evidence that closes it | Issue and owner |
|---|---|---|---|
| Agent launch | Package/driver binding over actual host | Scripted accepted candidate and cancellation trace | To assign |
| Task environment | One reviewed immutable input set and query backend | Query-order and counterfactual controls | To assign |
| Evidence handoff | Candidate plus trusted capture | Invented support/missing trace rejected | To assign |
| Verification/metrics | Reviewed oracle, checks and metric policy | Known-output controls and coverage report | To assign |
| Hosted integration | Same frozen inputs admitted and executed by service | Retained end-to-end result with enforced limits | After local conformance; to scope |

Record fixture limitations and reviewer disagreement beside the relevant task. After a model comparison, retain the result and explain what it does and does not establish. A read-only shadow report may guide task design; production impact and mitigation safety require additional evidence.
