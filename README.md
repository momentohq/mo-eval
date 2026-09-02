# mo-eval

mo-eval runs reproducible experiments on coding agents. You describe what to compare — which agent,
which model, which tasks, how many attempts — and it runs every combination in an isolated container,
grades the result with the task's own tests, and reports what passed.

This quickstart compares two clients against two models on one real Django bug: `mo` and Claude Code,
each on GLM-5.2 and Opus 5, twice each. Four arms, eight attempts.

Terms used throughout:

- **Client** — the coding agent under test: `mo` (Momento's own) or `cc` (Claude Code).
- **Task** — one SWE-bench issue, with its own container image and test suite.
- **Arm** — one client and model combination (the report card calls this a `variant`).
- **Cell** — one arm, one task, one attempt.

The commands run in order, each reading what the one before it wrote:

```text
  new  ──▶  stage  ──▶  plan  ──▶  run  ──▶  report
   │          │           │         │          │
   │          │           │         │          └─ turns the finished attempts into a report card, report.md
   │          │           │         └─ runs each cell in the task's own container, and grades it
   │          │           └─ freezes the spec into experiment-plan.json, the thing `run` executes
   │          └─ downloads the agent binaries and task records the spec names
   └─ writes experiment.yaml: the arms, the tasks, how many attempts
```

## 1. Check your machine

You need Docker running, and the task images are x86-64. On Apple Silicon that means enabling
**"Use Rosetta for x86_64/amd64 emulation"** in Docker Desktop → Settings → General: without it every
attempt runs under far slower emulation, and nothing at run time will tell you it is off. Linux arm64
cannot run these images at all.

## 2. Install

Everything mo-eval writes — bundles, agent binaries, plans, results, credentials — lives under one
directory. Make it, put the launcher inside, and put that directory on your PATH:

```bash
mkdir -p ~/mo-eval && cd ~/mo-eval
docker run --rm --platform linux/amd64 public.ecr.aws/r2g5j3j4/mo-eval:latest install \
  > mo-eval && chmod +x mo-eval
export PATH="$PWD:$PATH"
mo-eval --help
```

Nothing else lands on your machine; the rest runs in the image. You will see it download twice —
`install` pulls `latest`, then the launcher pins itself to that image's exact version and pulls it by
number, so a later `latest` cannot change what you are running mid-experiment.

Stay in this directory for the steps below, so that a path means the same thing inside the task
container as it does here.

Coming back in a new terminal? Run `cd ~/mo-eval && export PATH="$PWD:$PATH"` again.

## 3. Log in

The image carries its own `mo`, and each attempt mints its own gateway token from your login:

```bash
mo-eval mo login   # once; prints a URL and a code to open on your own machine
```

## 4. Compose the experiment

```bash
mo-eval new ./quickstart \
  --clients mo,cc \
  --models momento/zai-org/GLM-5.2,anthropic/claude-opus-5 \
  --tasks django__django-11099 \
  --size full \
  --repeats 2
```

```text
wrote quickstart/experiment.yaml
  4 arms, 2 repeat(s), 1 task(s) — 8 attempts
next:
  1. mo-eval stage quickstart/experiment.yaml
  2. mo-eval plan quickstart/experiment.yaml --experiment quickstart/experiment
```

Arms are the cross product of the clients and models you name. Everything else is identical across
them, which is what makes the comparison fair.

Agents are not deterministic, so `--repeats 2` runs each arm twice.

`--size` caps how long each attempt may run: `full` allows an hour, `smoke` thirty minutes for a
quicker, cheaper pass.

The bundle holds `experiment.yaml`, an empty `client/` for the binaries, and the home templates its
arms start from. Each arm records the agent version it measures, so the same spec stages the same build on
anyone's machine. The spec is an ordinary file — edit it for anything the flags do not cover.

## 5. Download what the experiment needs

Staging downloads what the spec pins: which `mo` build to measure, which Claude Code release the
`cc` arms drive, and which SWE-bench issue to solve.

```bash
mo-eval stage ./quickstart/experiment.yaml
```

```text
fetching mo 0.131.0
fetching claude 2.1.238
fetching 1 task record(s)
staged mo 0.131.0 (digest verified) → quickstart/client/mo
staged claude 2.1.238 (digest verified) → quickstart/client/claude
staged task records → quickstart/instances.jsonl
```

Both versions are pinned by the spec — yours may differ from these.

No flags needed: the spec already says what to fetch. Safe to re-run — anything already downloaded and
matching its digest is left alone.

To measure a different build, change that arm's `version:` in the spec. To supply your own,
replace `version:` with `binary: ./client/mo` and put the executable there — staging then leaves that
arm alone. `--only client`, `--only tasks` narrow what is fetched; nothing widens past the spec.

## 6. Run

```bash
mo-eval plan ./quickstart/experiment.yaml --experiment ./quickstart/experiment
mo-eval run ./quickstart/experiment/experiment-plan.json --concurrency 2
```

Planning validates the spec and writes the plan file that `run` executes.

The first run pulls the task's container image, about 4 GB, so expect several quiet minutes before the
agent starts. Progress then renders live in the terminal.

Re-running skips finished cells, so an interrupted run picks up where it stopped.

## 7. Read the results

```bash
mo-eval report ./quickstart/experiment
cat ./quickstart/experiment/report-card.txt
```

The card ends with a head-to-head comparison of every arm:

```text
variant               passes     cost   $/pass  avg time
mo-glm-5.2               2/2   $0.081   $0.040      1.2m
mo-claude-opus-5         2/2   $0.327   $0.163      1.0m
cc-glm-5.2               2/2   $0.186   $0.093      1.1m
cc-claude-opus-5         2/2   $0.865   $0.433      1.0m
```

Above it, a scoreboard marks each attempt: `█` passed, `▒` the official scorer rejected. Whether an
agent solves a given task varies between runs.

`report.md` is a fuller written summary, and `cells.json` has one row per cell — eight here —
including any that failed or never ran.

## Run a new experiment

One bundle is one experiment. Compose into a **new** directory each time, and both stay on disk to
compare:

```bash
mo-eval new ./kimi-vs-glm \
  --clients mo \
  --models momento/zai-org/GLM-5.2,momento/moonshotai/Kimi-K3 \
  --tasks django__django-11099,django__django-10973,astropy__astropy-12907 \
  --size smoke \
  --repeats 3

mo-eval stage ./kimi-vs-glm/experiment.yaml
mo-eval plan  ./kimi-vs-glm/experiment.yaml --experiment ./kimi-vs-glm/experiment
mo-eval run   ./kimi-vs-glm/experiment/experiment-plan.json --concurrency 2
```

Two arms, three tasks, three repeats — eighteen attempts. `new` prints the `stage` and `plan`
commands for the bundle it just wrote, so you can copy them rather than retype the paths.

`--models` takes full gateway routes. Each arm is named for its client and the last segment of its
route — `momento/moonshotai/Kimi-K3` becomes `mo-kimi-k3` — and that name is what labels it in the
report card and `cells.json`.

## Extend an existing experiment

To add tasks or arms to a bundle you have already run, edit its `experiment.yaml` — add ids to
`tasks:`, or another arm — then stage what the edit now needs and plan into a **new** experiment
directory beside the old one:

```bash
$EDITOR ./quickstart/experiment.yaml
mo-eval stage ./quickstart/experiment.yaml                                    # fetch what is new
mo-eval plan  ./quickstart/experiment.yaml --experiment ./quickstart/round-2  # not ./quickstart/experiment
mo-eval run   ./quickstart/round-2/experiment-plan.json --concurrency 2
```

The new directory is a must. A plan is frozen when it is written and holds its own copy
of everything it ran, so re-planning over the old directory is refused.

Report each directory separately; the earlier results stay exactly as they were.
