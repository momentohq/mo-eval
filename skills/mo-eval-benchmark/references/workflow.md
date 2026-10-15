# Benchmark curated tasks

Use the current task catalog, agent catalog and model routes; do not infer available tasks, agents,
routes or their compatibility from this guide. A job spends gateway tokens and a shared lane.
Submit only when the person has authorized this paid job; show the exact request and planned trial
count if authorization is not yet given. The three server guides below cover a first run,
comparison design and result analysis.
Where a guide below says to wait for a go-ahead, authorization already given for that exact job
counts; do not request it twice.

## First run

Walk me through my first mo-eval job. I want a result quickly, so aim for the smallest job that
works end to end, not one that answers a research question yet.

## 1. Gather what I can choose from

Call `whoami`, `list_agents`, `list_tasks`, and `list_models`, the last with `agent_id` set to `mo`,
all before telling me anything. If `list_tasks` lists nothing, say there is
no task I can run yet and stop.

From `whoami`, tell me the address I sign in with — it is what a colleague needs in order to share a
job with me — and whether this token may submit jobs, which is `may_submit`. Report `may_submit` as
it comes; do not infer what a token can do from the names of its scopes.

If `may_submit` is false, say so now rather than at step 5: everything below works except submitting,
and if the token lacks the write scope, getting it means signing in to this server again and
approving the second permission. If the token has it and `may_submit` is still false, this
deployment is not admitting my account to submit yet, and signing in again will not change that.
Nothing else about my account gates what follows, so do not send me back to log in for any other
reason.

A job pairs a task with an agent and a model route, and each is picked from more on offer. Tell me
this quickstart uses the `mo` agent, and that I pick the task and the model.

## 2. Show me tasks to choose from

Each task may carry its title, category, size, test count and its suite's language; a task without
them lists by id alone. For each language the list holds, suggest one or two tasks, favouring:

- size `S`, the smallest source changes, so the agent has least to write;
- a test count, so the result is graded against named tests.

Show them in one table, a row per task, with whichever of its title, category, size, test count and
language it has, and let me pick one.

## 3. Show me models to choose from

Pick the model first: show me, in a table, the first one or two routes of each provider in the
order `list_models` gives them, and say I can ask for the whole list. List them as they are, with no
remarks on cost or speed. Let me pick one.

## 4. Propose the job

One task and agent pair, one trial, at the `smoke` size: each attempt at the trial capped at
60 minutes, with its agent stopped at 30 minutes or
100 turns.

Do not estimate how long the job will take: it waits in a shared queue first, and how long an
attempt runs depends on the task. State the trial count and the caps, show me the exact `submit_batch_job`
arguments with one `items` entry whose `task` holds the selected `repo`, `suite_id`, and `task_id`,
whose `agent.agent_id` is `mo` and `agent.model_route` is my choice, and whose `trial_count` is 1. Wait for my
go-ahead.

## 5. Submit and follow

On my go-ahead, call `submit_batch_job` and give me the job id. Then tell me, in words close to: "Ask me
for an update whenever you like, e.g. 'how's the job?'. When it's done, I'll show the summary." Add
that if my client can repeat a request on a schedule, I can have it ask for me.

Call `get_job_status` only when I ask, and no more than once every few minutes: a job is preparing
until a lane has prepared it, then running once a lane takes up its trials, and ends done; it ends
failed, unreadable or incomplete if it cannot be prepared or reported. If it ends that way, read me
what `get_job_status` says rather than resubmitting.

If I ask to stop my job, call `cancel_job` with its id. Follow `get_job_status` until shutdown is
acknowledged as cancelled; while cancelling, active cleanup remains pending. Retain its completed
evidence and original planned trial count when reporting the partial result.

## 6. Show me the result

When it ends done, its `get_job_status` answer may carry a `tldr`, the summary mo-eval wrote for it.
If it carries none, skip this and do not write a summary of your own. Otherwise:

- `ready`: show me `tldr.saved.tldr.post_text` verbatim, before anything else;
- `building`: say the summary is on its way, and that `analyze-job` will show it;
- `unavailable`: give me its `reason` in one line.

Then point me at this server's `analyze-job` prompt with the job id, for what the result does and
does not support, and at its `design-job` prompt for a real comparison: more tasks, a second arm,
more trials.

If anything along the way fails or confuses me, offer to tell the mo-eval team with
`submit_feedback`, and show me what it would send first.


## Design a comparison

Help me design and submit a mo-eval job. What I want to find out:

the user's stated benchmark question

Design it with me before submitting anything. A job spends real gateway tokens and holds a shared
lane for as long as it takes, so the cost of a badly-shaped job is hours and money, and it is not
refunded by noticing afterwards.

## Work out what would answer the question

Say back what the job has to show to settle it, and what result would change my mind. If the goal
names a comparison, name the one variable that differs between the arms; if it names more than one,
the job cannot attribute a difference to either and the design needs fixing now rather than at
analysis.

If the question cannot be answered by a job of this shape — it needs a benchmark we do not have, or
evidence a trial does not capture — say so instead of designing around it.

## Pick the pieces

Call `whoami` first, for `may_submit`: a design I cannot submit is worth knowing about before we
shape it rather than after. An empty `list_tasks` means the catalog holds nothing I can run, not
that my account is missing something.

Then use `list_tasks` for the repository and suite; only what it lists can be run, and the ids are
case-sensitive exactly as it gives them. Each task may carry its title, category, size, test count
and its suite's language. Use them to choose tasks that fit the question: categories that match what
it asks about, size `S` tasks for a first pass since they cost least, and tasks with a test count so
results are graded against named tests. Say which tasks you picked and why.

- **Arms.** One per thing being compared, 1 to 8, each distinct. Two arms that differ in agent
  *and* route measure neither. Give every arm a `name` when more than one shares an agent, route and
  effort, since results are labelled by it.
- **Agents and routes.** Call `list_agents` before choosing an agent. Pick the model first, since it
  is usually what a job compares: offer me routes from `list_models`, then take each arm's agent
  selector from that route's `compatible_agent_ids`. The field contains `list_agents` `agent_id`
  values. When the agent is what differs, offer only routes whose `compatible_agent_ids` hold every
  selected agent.
- **`trials_per_condition`, the trial count.** 1 to 5 trials of each arm on each task. One trial
  cannot distinguish a real difference from variance at all. Two can disagree but cannot say which
  way a task leans; 3 is the smallest that gives a majority, so reach for 3 when the goal is a
  comparison. If cost rules that out, say the job will not support a claim about small differences,
  rather than running it and discovering that.
- **`size`.** `smoke` (60 minutes per attempt; 30 minutes
  and 100 turns per agent) or `full` (180 minutes;
  60 minutes and 400 turns). **Default to `smoke`.** `full` costs
  several times more and holds the lane far longer; reach for it only when a result has to support
  a claim and `smoke` has already shown the shape.

## Cost it before submitting

Multiply: **arms × tasks × trials of each = trials**, each one an agent working for up to its size's
cap. State that number and a rough token cost, and stop for my confirmation before calling
`submit_experiment_job`.

If the count is large, propose the smaller job that would answer the same question — a few
representative tasks at `smoke` first, then widen once the shape is known. A job that nobody waits
for is worse than one that was too small.

## Submit and follow

Call `submit_experiment_job` only once I have agreed the shape. It refuses a malformed setting before anything
is queued; a setting only the lane can refuse fails the whole job before any agent starts, so read
what it says rather than retrying.

Then give me the `job_id`, and tell me it is followed with `get_job_status`.


## Read a completed comparison

Analyse mo-eval job `<job_id returned by submit_experiment_job>` and report what it shows.

Work from the data, not from this text: the numbers come from the parquet, and everything below is
about *which* numbers to compute.

## Start with the job's TL;DR

Call `get_job_status` with `job_id: "<job_id returned by submit_experiment_job>"`. A finished job may carry a `tldr`: a summary mo-eval
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

Call `query_job_results` with `job_id: "<job_id returned by submit_experiment_job>"`. It answers with one of three `state` values,
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

