# Evaluate one configuration

Use this workflow to establish a baseline for one agent configuration, read its results, and decide
what to try next. For a controlled comparison between configurations, use `compare` instead.

If this is the caller's first authenticated job, read the separate `quickstart` workflow first. It
covers account status, choosing a small task and model, and confirming the initial one-trial job.

## Run or repeat a baseline

Call `list_agents`, `list_tasks`, and `list_models` for the current choices; do not infer an agent,
task, or model route from this guide. Propose a `submit_batch_job` request with one or more task
items that all use one agent configuration. Set each item's `trial_count` explicitly, and keep that
configuration fixed across every item and trial. Show the exact request, per-item trial counts, and
spending limits, then wait for the caller's authorization before submitting.

To repeat a baseline, use the same tasks, configuration, and per-item trial counts with
`submit_batch_job`. If the caller changes the configuration, make the changed run a new baseline
rather than treating it as a comparison.

## Read and iterate on the baseline

Read the completed job through the server's result tools. Report the eligible trial count, coverage,
cost, and any unavailable or incomplete result before proposing another run. Keep the configuration
fixed unless the caller asks to change it; a changed configuration begins a new baseline.

Analyse mo-eval job `<job_id returned by submit_batch_job>` and report what it shows.

Work from the data, not from this text: the numbers come from the parquet, and everything below is
about *which* numbers to compute.

## Start with the job's TL;DR

Call `get_job_status` with `job_id: "<job_id returned by submit_batch_job>"`. A finished job may carry a `tldr`: a summary mo-eval
computed from the job's trial results, written to be shared. If it carries none, go on with the
analysis. Otherwise, before any analysis:

If status is cancelling or cancelled, state that execution was stopped and use the admitted
planned_trial_count as the denominator. Report cancelled trials separately from verifier failures;
captured result frames describe a partial subset and cannot shrink that planned count.

- `ready` — present `tldr.saved.tldr.post_text` verbatim, as the first thing the reader sees: it is
  the headline, its supporting lines and how much they can carry, and it never names a private
  repository. If `tldr.saved.tldr.next_step` is set, follow it with one line: "Try next:" and that
  step. Then offer what the reader can do from here:
  - share the post as written;
  - when `tldr.saved.tldr.next_trials_per_condition` is set, run it again with more trials:
    `submit_experiment_job` with this job's repository, suite, tasks and arms, and `trials_per_condition` set
    to that number;
  - see why a task failed: `list_artifacts` and `read_artifact` for that task's attempts;
  - go further into the numbers, which is the analysis below.
- `building` — say the summary is on its way and go on with the analysis; `get_job_status` has it
  after `retry_after_seconds`.
- `unavailable` — give the `reason` in one line and go on with the analysis.

Present the TL;DR; do not compute from it. Every number below comes from the rows,
never from the TL;DR, and a comparison with another job starts from that job's rows too.

## Get the rows

Call `query_job_results` with `job_id: "<job_id returned by submit_batch_job>"`. It answers with one of three `state` values,
and all three need handling:

- `building` — the build is running. Call again after `retry_after_seconds`, with the same arguments.
- `ready` — download the `url` and load it with the `read_with` line. It is parquet: load it with
  code, never fetch it as text.
- `failed` — **stop and report it.** The build produced no rows, so there is nothing to analyse and
  no analysis to attempt. Quote `failure` if it is set; if it is not, say the build did not finish
  and its logs are the record. Do not retry it: a build that failed this way fails the same way
  again, and a rebuild is the caller's decision, not yours.

One row per trial: one arm, one task, one `trial_number`.

## The denominator is the whole job

Every row carries its `disposition` under the metric policy `eligible-success-with-coverage/1`: one of the four
populations below, each listed with the rules that assign it. `disposition_rule` names the rule that
decided the row. The populations answer different questions. Using the wrong one is the mistake this
analysis exists to avoid, because it is invisible in the result — a rate over the wrong denominator
looks exactly like a rate.

- **Eligible** — `failed_by_stop`, `judged_pass`, `judged_fail`, `empty_candidate`.
  The agent's work, measured: a pass or a fail. **Quality rates go over these and only these.**
- **Missing** — `not_attempted`, `no_complete_attempt`.
  The trial has no result: it never ran, or no attempt completed. Not a failure: it is coverage the
  rate does not have, so say how much.
- **Invalid** — `unselectable`, `evidence_missing`, `evidence_tampered`, `evidence_invalid`.
  A result exists, but its evidence cannot stand as a measurement. Exclude from everything, and if
  there are any, say so first: the job's record is at fault, not the agent.
- **Excluded** — `contaminated`, `no_result`, `budget_cap`, `unaccepted_protocol`, `invalid_task`, `broken_verifier`, `infrastructure_fault`, `never_measured`, `unknown_stop`, `unjudged`.
  A valid result the policy leaves out, and never a failure: the agent looked up the task's own fix,
  produced nothing usable, hit a spend cap or never started, or no verifier could judge its
  candidate. Exclude from quality, and read the rule for where to look. If there are many, say so
  first: a job mostly made of these is not a result about models at all.

**Cost is different.** It goes over every row where the work actually happened — the agent spent
those tokens whether or not its trial is eligible. Do not reuse the quality denominator.

## Say what was dropped

Report the four population counts, and the rule behind every row that is not eligible, before any
rate. A pass rate of 60% over 30 eligible rows of 54 is a different claim from 60% over 54, and the
reader cannot tell them apart from the number.

Check `cost_complete` before quoting cost: where it is false the usage join did not finish and the
total is a floor, not a total.

## Show the spread across trials

If `trial_number` has more than one distinct value, the spread is the finding — report it, not just
a mean. A task that passes on two of three eligible trials is a different animal from one that
passes on none, and a single mean over every row hides which tasks were which. Report each task's
passes over its eligible trials, with its missing, invalid and excluded counts beside them, rather
than an average of averages.

If `trial_number` is `1` on every row there is exactly one trial per arm and task: say that the job
cannot distinguish signal from variance, rather than reporting a rate as though it could.

## Comparing arms

Group by `agent_configuration_name`. Before quoting any difference, check the arms have
**comparable denominators**: if one arm has fewer eligible rows than the other, its quality rate is
over a different and smaller population, and the difference you are about to report is partly that.
Say so when it happens.

A difference of a few points on a handful of tasks is noise. Quote the counts alongside the rate so
the reader can judge, and do not describe a difference as a result unless the eligible counts are
close and large enough to carry it.

## Useful columns

`passed` is the verdict to count: it is true only on an eligible row whose `disposition_rule` is
`judged_pass`. `display_outcome` is a label for display, not the verdict: a `contaminated` row can
read `resolved` and still not count. `verifier_verdict` is **not** the verdict either — it is the
verifier's own opinion, and it can pass an agent that declined, stalled or timed out, which the
policy fails as `failed_by_stop`. Count `passed`; read `verifier_verdict` and `stopping_reason`
only to explain a trial.

The rest: `display_outcome`, `agent_configuration_name`, `agent_id`, `model_route`,
`agent_configuration`, `task_id`, `trial_number`, `cost_usd`, `cost_complete`, `total_tokens`,
`turns`, `agent_duration_seconds`, `scorer_exit_code`, `scorer_output_tail`, `last_error`.

For a single surprising trial, read `scorer_output_tail` and `last_error` **before** theorising from
anything else — the scorer usually already said what happened.

## Report

After the TL;DR, lead with the verdict and the denominator it rests on. Then the per-arm table,
then every row that is not eligible, by rule, then anything that makes the job untrustworthy. If the
job cannot answer the question asked of it, say that first rather than last.

