# Operating a fleet

What the fleet does by itself, and the few things that need you. Paths are relative to the fleet
home (`$TAUCETI_FLEET_HOME`, default `~/.tauceti-fleet`).

## The shape follows the backlog

After every round, the worker runs `tauceti-fleet reconcile` through its round-done hook. The
reconcile reads the counts that round's survey left behind, so it costs no GitHub request, and
reshapes the fleet:

- **Authors** (`<name>-c*` pinned to Claude, `<name>-x*` running `auto`) are enabled only while the
  fleet's account has fewer than `authoring.max_open_prs` open PRs in scope (the worker's default is
  8). At that many or more the worker's own backpressure rule would make them decline every round, so
  they stay defined but disabled.
- **Fixers** (`<name>-fix*`) run fix, fix-ci and rebase. They are sized by the fix backlog: the
  account's PRs labelled `awaiting-author` or `ci-failed`. There are 3 while authoring is blocked or
  the backlog is 8 or more, otherwise 2 with a backlog of 6 or 7 and 1 below that, never more than
  there are PRs to fix. Odd-numbered fixers are pinned to Claude; even-numbered ones run `auto`.
- **Reviewers** (`<name>-rev*`) run `auto`: 2 once two or more authors and fixers are active, else 1.
  Reviewing other people's PRs is what the fleet owes the project for the reviews its own PRs get.

An `auto` worker uses Codex while Codex's usage window has room and Claude otherwise, so that half
of the fleet never parks when one subscription runs dry.

**Config changes wait for the round to end.** The manager restarts a worker whenever its entry in
`workers.toml` changes, which mid-round would throw away a build. The reconcile keeps a mid-round
worker's old entry and switches it at a later reconcile that finds it between rounds; the reconcile
line lists these as `deferred (mid-round)`. `tauceti-fleet reconcile --dry-run` shows what a pass
would do.

## The GitHub gate

Every request the workers and the tool make as the fleet's account goes through one gate store
(`gate/`) with rolling-hour budgets: `gate.mutations_per_hour` for writes and `gate.reads_per_hour`
for reads. A worker that sees any identity other than `fleet.github_login`, or a credential error,
halts and stays halted until you look: `tauceti-fleet clear-halt` shows the incident and clears it.

```bash
tauceti-fleet gate status
```

```bash
tauceti-fleet gate report --since 24h
```

The status line lists budgets used, pushes per repository, and publications (PR creations, pushes,
comments) still in progress or parked. A round that failed before publishing leaves a parked entry
with no remote effect; `tauceti-fleet gate publication prune` archives those.

Budgets are staging controls, not guarantees. Raise them only after measuring a quiet week.

## The Claude login pool

Renewing a Claude access token revokes the previous one immediately, so workers that share one login
kill each other's rounds. The fleet keeps a **pool** of login chains, `logins/claude-1`,
`logins/claude-2`, … each an ordinary sign-in to the same subscription. Chains are named for the pool,
never for a worker: at every reconcile each Claude-capable worker, and the periodic runner, leases one
(`logins/leases.json`), keeps it while it exists, and releases it when it is disabled or renumbered.
Reshaping the fleet never asks for a new sign-in.

Nobody has to renew anything. A leased chain is renewed by its worker before each launch, early
enough to outlast the round, including while the worker waits out a usage limit. A free chain is
renewed by the tool, from every reconcile and every half hour from the live view. The only case that
needs you is a chain that lost its refresh token; the live view's `credentials` row names it.

```bash
tauceti-fleet logins
```

prints the chains, the leases, and the exact sign-in line for each chain still missing. Workers left
without a chain share `~/.claude`, and `logins` says so.

## Things that need you

The live view shows a `needs you` badge and panel; `tauceti-fleet attention` prints them in full.

- **A round declined to act, and the decide stage handed it to you.** A fix or rebase round whose
  agent could not act files an incident with the agent's last words and the PRs it named. The decide
  stage (below) rules on it first, and only two rulings reach this list: `roadmap`, with a drafted
  roadmap change, and `escalate`, with its analysis, any recommendation and the evidence.
  `--file-roadmap PR` files a drafted change. An agent applies it to the roadmap's README on a
  branch, and you read the diff. On your yes the change is opened as a TauCetiRoadmap PR from the
  account's fork (`--open-roadmap PR` does this without asking; `--show-roadmap PR` shows it again). The agent may also edit the roadmap's `Suggested.lean`, which is then built as TauCetiRoadmap's CI builds it, together with every `Suggested.lean` that imports it. The TauCeti PR then waits for the roadmap PR.
  A proposal may name up to three roadmaps. That happens when a name one roadmap pins is used by another, for example a declaration `#check`ed by a consumer's `Suggested.lean`, which cannot be renamed in either alone without breaking the other's build. The change is then one PR touching each of them, and it may touch only the roadmaps the proposal names.
  `--lookup` resolves the named PRs; `--ack PR` or `--ack all` archives the incident once handled. A
  decline the stage has not ruled on within 2 hours is listed too. So are the stage's rulings from
  the last 24 hours, closes included, though they need nothing from you.
- **A review exchange hit its cap**, or a review errored three times without a verdict. The worker
  stops spending on that PR until you look.
- **A target-list item whose PR closed without a recorded verdict.** The curator cannot tell whether
  the work landed elsewhere, so it asks: mark it `[ ]` to re-author or `[x]` if done.
- **A target list that diverged from its repository** (`targets-diverged`): a curation committed
  here conflicts with one pushed elsewhere. See
  [target-lists.md](target-lists.md#sharing-a-list).

A worker in a long backoff can be restarted between rounds with `tauceti-fleet restart ID`, or
`--when-idle` to queue it for the end of the current round.

## The progress-report worker

`<name>-prog1`, off until `enabled = true` under `[progress]`, writes roadmaps' STATUS.md and
PROGRESS.md reports through TauCetiProgress, as pull requests to TauCetiRoadmap that its merge gate
lands without a human; each landing is announced on Zulip. It is a worker, not a periodic round: it
looks for work all the time and writes a report as soon as a roadmap qualifies. With N the PRs merged
into a roadmap's window and T the days since its last report landed, a roadmap qualifies when N > 0
and either it has been declared complete (archived under `Completed/`) or N + T > 10
(`progress.threshold`). A roadmap never reported qualifies with its first PR. The merge gate allows
one report per roadmap per 6 hours, and the planner respects that. Among the qualifying roadmaps the
one with the most PRs is written. Another operator's open report holds its roadmap for 8 hours, so
the worker does not duplicate it; after that it is treated as stuck.

This needs a TauCetiProgress build with the `threshold` strategy: set `progress.repo` and
`progress.ref` to one (roed-math/TauCetiProgress, branch `feat/threshold-strategy`, until it is
upstream).

Between reports the worker only polls, cheaply: it plans again when the published documentation, or
TauCetiRoadmap's `main`, has moved, or when the last plan's "next qualifies at" has passed, and at
least hourly. The live view's `reports` line shows what it is landing and its last assessment.

It sees each report of its own through to landing, following the rules a hand-run lander learned
landing 29 reports on 2026-09-27. The gate lands a report by compare-and-swap, so each landing leaves
every other open report behind `main`. The worker brings a report up to date, but only while `main`
builds. It asks the gate again, at most twice, when the gate has been quiet for 20 minutes after a
green build. It ignores the gate's first-pass "build not completed" and any refusal about an earlier
head. It files a `progress-stuck` item under `attention` for anything that needs you: a build that
fails on an up-to-date report while `main` builds, or a refusal that survives the re-asks. At most
`progress.max_open` (2) of its reports are open at once.

Before a report is opened, the writing model is given the library's source at the window's end to
check each layer's state against. It must run `tauceti-progress check` and fix what that reports:
the prompt's word limits and headings, documentation links copied from the supplied material and
still resolving, and no layer the previous report assessed turned `unassessed`. A report that still
fails after one repair pass is not opened.

## The periodic rounds

Two stages are not about one of the fleet's own PRs and run on a cadence rather than in a loop, as
one-shot rounds under the id `<name>-periodic`, started by the reconcile hook or the live view when
due. One runs at a time.

- **curate**, every 6 hours, keeps the target list true. It checks each in-flight item's PR: merged
  marks it done, closed with a recorded subsumption verdict marks it done and names the PR that
  subsumed it, closed without one is left for you. For the items the authors would take next it also
  looks for the milestone's declarations on main, and asks the model; only an explicit verdict with
  named evidence marks an item "landed elsewhere". When the list is tracked in git it pulls before
  reading it, commits the change, and pushes it when the fleet's account can push to that
  repository, so several fleets or hosts can share one list
  ([target-lists.md](target-lists.md#sharing-a-list)).
- **decide**, on unless `decide.enabled = false`, rules on declined rounds. It runs within about 10
  minutes of a new decline, and every 6 hours while a ruling waits on something. Without a model it
  settles declines that events have overtaken: the PR merged, closed or has a new head. It notes an
  authoring decline with no target. It turns a `wait` into a `retry` once what it waited on has
  merged or reached an open PR. It puts the rest to the model (the curator's model), with the PR, its
  scoreboard and threads, the fixer's account, the open PRs, the target list and the roadmap and
  rubric checkouts. The model rules one of these, and the worker's code checks each ruling before
  acting on it:
  - `retry`: a fixer tries again, and the ruling's note tells it what is new. Allowed once per head.
  - `wait`: on open PRs or items already in the target list.
  - `prerequisite`: the missing roadmap milestone is added at the top of its area in the target
    list, so the authors write it next, and the PR waits for it. The scope rubric accepts a
    prerequisite stage that is in an open PR.
  - `close`, when `decide.close = true`: closes the PR as subsumed and posts the evidence as a
    comment. The PR must be the account's own and carry no hold label. Every merged PR it names must
    have merged, and every declaration it names must be on main. At most `decide.max_closes_per_day`
    (default 3) close each day. If any check fails, the ruling becomes an escalation.
  - `roadmap`: a drafted change, in `<fleet home>/gate/decisions/`. You file it with `attention
    --file-roadmap`, since agents never open TauCetiRoadmap PRs on their own. Once that roadmap PR
    merges, the TauCeti PR's fixer is told to cite it on the scope finding.
  - `escalate`: anything else, including a recommendation to close the PR.

  Besides a close, the stage writes only the fleet's own records and the target list.

```bash
tauceti-fleet periodic
```

```bash
tauceti-fleet periodic --now curate
```

## The Mathlib cache pool

Each worker hard-links Mathlib's compiled files from a shared pool in `~/.cache/mathlib` before a
round, and bubble mounts them into the container, so a round never downloads Mathlib itself. The
reconcile notices which Mathlib revisions main and the fleet's open PRs pin, and fetches any missing
revision in the background (`warm-pool.log`), so a Mathlib bump needs no action. The live view's
`mathlib pool` row shows needed and warm counts.

## bubble's cache proxy

The artifact-cache daemon on port 7655 serves every container's downloads. Without kim-em/bubble#342
it wedges after 256 connections: rounds hang in `lake cache get` while `bubble cache status` still
says running. The reconcile restarts a daemon that looks wedged and records it in `watchdog.log`; with
the fix installed that should never fire.

## Logs

Every worker writes durable logs under `state/logs/<id>/`; the periodic rounds under
`state/logs/<name>-periodic/`. `tauceti-fleet logs ID -f` follows one. The live view shows health,
the phase and target of each round, the last log line, subscription usage left, the gate, and the
pool; its `recent events` panel fills the rest of the screen.
