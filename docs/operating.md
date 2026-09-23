# Operating a fleet

What the fleet does by itself, and the few things that need you. Paths are relative to the fleet
home (`$TAUCETI_FLEET_HOME`, default `~/.tauceti-fleet`).

## The shape follows the backlog

After every round, the worker runs `tauceti-fleet reconcile` through its round-done hook. The
reconcile reads the counts that round's survey left behind, so it costs no GitHub request, and
reshapes the fleet:

- **Authors** (`<name>-c*` pinned to Claude, `<name>-x*` running `auto`) are enabled only while the
  fleet's account has fewer than 8 open PRs in scope. At 8 or more the worker's own backpressure rule
  would make them decline every round, so they stay defined but disabled.
- **Fixers** (`<name>-fix*`) run fix, fix-ci and rebase. There are 3 while authoring is blocked,
  otherwise 2 with 6 or 7 PRs awaiting the author and 1 below that, never more than there are PRs to
  fix. Odd-numbered fixers are pinned to Claude; even-numbered ones run `auto`.
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

- **A round declined to act.** A fix or rebase round whose agent found nothing to do, usually
  because main already has what the PR adds, files an incident with the agent's last words and the
  PRs it named as subsuming this one. Closing a PR is always a human act. `--lookup` resolves the
  named PRs; `--ack PR` or `--ack all` archives the incident once handled.
- **A review exchange hit its cap**, or a review errored three times without a verdict. The worker
  stops spending on that PR until you look.
- **A target-list item whose PR closed without a recorded verdict.** The curator cannot tell whether
  the work landed elsewhere, so it asks: mark it `[ ]` to re-author or `[x]` if done.

A worker in a long backoff can be restarted between rounds with `tauceti-fleet restart ID`, or
`--when-idle` to queue it for the end of the current round.

## The periodic rounds

Two stages are not about the fleet's own PRs and run on a cadence rather than in a loop, as one-shot
rounds under the id `<name>-periodic`, started by the reconcile hook or the live view when due.

- **curate**, every 6 hours, keeps the target list true. It checks each in-flight item's PR: merged
  marks it done, closed with a recorded subsumption verdict marks it done and names the PR that
  subsumed it, closed without one is left for you. For the items the authors would take next it also
  looks for the milestone's declarations on main, and asks the model; only an explicit verdict with
  named evidence marks an item "landed elsewhere". When the list is tracked in git it commits the
  change, and pushes it when the fleet's account can push to that repository.
- **progress**, off until `tauceti-fleet periodic --enable progress`, writes one roadmap's STATUS.md
  and PROGRESS.md report through TauCetiProgress, as a PR to TauCetiRoadmap. It is tried every 2
  hours; TauCetiProgress itself waits 8 hours after the last landed report. `progress.strategy =
  "rotate"`, with a TauCetiProgress that supports it, reports the stalest roadmap first instead of
  the busiest.

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
