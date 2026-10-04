# tauceti-fleet

Run a fleet of [TauCetiWorker](https://github.com/kim-em/TauCetiWorker) workers against
[Tau Ceti](https://github.com/TauCetiProject/TauCeti), aimed at one goal: an **operator target list**
of roadmap milestones you want proved. The fleet authors PRs for those milestones, fixes and rebases
its own PRs, reviews other people's PRs in return, and keeps the target list true as work lands.

One command, `tauceti-fleet`, shapes the fleet from the backlog, drives the worker's own manager,
keeps a pool of Claude logins that renew themselves, runs everything through a shared GitHub
budget, and shows a live view.

```
bin/tauceti-fleet        the tool
targets/                 target lists; each fleet points at one of them
docs/setup.md            installing a host, each user on it, and several fleets on one host
docs/operating.md        what the fleet does on its own, and what needs you
docs/target-lists.md     writing a target list, and sharing one
docs/troubleshooting.md  symptoms, what causes them, and the fix
```

Everything about one particular fleet lives in its **settings file**, outside this repository. The
only fleet-specific files here are the target lists.

## What you need

- **A host.** Ubuntu with Incus, so that every round runs in an egress-denied container (bubble).
  Each fleet runs as its own Unix user, which needs no sudo and, through `incus-user`, is not
  root-equivalent either.
  Ten workers run on 32 cores and 96 GB of memory. Disk runs out first: about 20 GB per worker
  checkout, plus the Mathlib cache. macOS works without the sandbox
  (`up.sandbox = "host"`), which is fine for trying it and not for leaving it unattended.
- **A GitHub account for the fleet, and only for the fleet.** Every request goes through a budget
  (the gate) because automated volume is what GitHub's abuse detection looks for, and an account
  can be suspended for it. Never sign the fleet in as a person.
- **A Claude subscription.** The fleet signs it in several times, once per login chain, and spends
  it. A **Codex** subscription is optional: `auto` workers use Codex while it has room and Claude
  otherwise.
- **A target list**: the milestones you want, from the roadmaps in
  [TauCetiRoadmap](https://github.com/TauCetiProject/TauCetiRoadmap). See
  [docs/target-lists.md](docs/target-lists.md), or start from the one in `targets/`.

## How a fleet works

- **Workers** are long-running loops, each a TauCetiWorker process with a role. **Authors** take the
  next eligible milestone on the target list and open a PR for it. **Fixers** answer review, repair
  CI and rebase the fleet's own PRs. **Reviewers** review other people's PRs, which is what the fleet
  owes the project for the reviews its PRs get.
- After every round the worker calls `tauceti-fleet reconcile`, which **reshapes the fleet** from the
  backlog: more fixers when many PRs need work, no authors while too many PRs are open.
- Every GitHub request, from the workers and from the agents inside their rounds, passes **the gate**:
  rolling-hour budgets for reads and writes, and a halt on any identity but the fleet's account.
- Workers **claim** what they work on in a repository shared by every fleet in the project
  (`TauCetiProject/tauceti-claims`), so fleets, yours and other people's, never duplicate a PR or a
  fix.
- Claude renews its access tokens by revoking the old ones, so the fleet keeps a **pool of logins**,
  one per concurrently running worker, and renews them itself.
- Periodic rounds keep the **target list true** (the curator) and rule on rounds whose agent declined
  to act (the decide stage). What needs you is collected in one place: `tauceti-fleet attention`.

## Quick start

On a host prepared as in [docs/setup.md](docs/setup.md):

```bash
tauceti-fleet init --name gq2 --targets ~/tauceti-fleet/targets/gq2_axiom_targets.md --github-login YOUR-BOT
tauceti-fleet logins     # prints one `claude auth login` line per login chain still missing
tauceti-fleet round      # one supervised round first; read its log and any PR it opened
tauceti-fleet up         # then the fleet; the live view opens
```

`up` starts in **pilot mode** unless you change it: one Claude author and no `auto` author, rounds
sandboxed in bubble, and no emoji reactions or automatic stuck-review issues on GitHub. Set
`up.pilot = false` in the settings, or pass `--no-pilot`, for the full shape once the pilot has run
cleanly.

## The fleet home and its settings

A fleet lives in one directory, its **home**: `$TAUCETI_FLEET_HOME`, default `~/.tauceti-fleet`.
It holds the settings (`fleet.toml`), the generated worker config (`workers.toml`), the GitHub gate,
the Claude login pool, and every worker's logs (`state/logs/<id>/`). To run a second fleet as the
same user, give it another home and export `TAUCETI_FLEET_HOME` for every command about it.

`init` writes `fleet.toml` with comments; edit it afterwards as you like.

| setting | meaning | default |
|---|---|---|
| `fleet.name` | short lowercase word; worker ids are `<name>-c1`, `<name>-fix1`, `<name>-rev1`, … | required |
| `fleet.targets` | the target list the authors work through; several fleets may share one (docs/setup.md) | required |
| `fleet.github_login` | the GitHub account every worker must act as; any other identity halts the worker | required |
| `fleet.claim_repo` | the project-wide claim namespace; every fleet must agree on it | `TauCetiProject/tauceti-claims` |
| `paths.worker` | a TauCetiWorker checkout (see Requirements) | `~/TauCetiWorker-v2` |
| `paths.roadmap` | a TauCetiRoadmap checkout, to check the list's areas are real roadmaps | `~/TauCetiRoadmap` |
| `up.pilot` | start in pilot mode | `init` writes `true` |
| `up.sandbox` | `bubble` (egress-denied containers) or `host` | `init` writes `bubble` |
| `up.pace` | the worker's pacing curve, `time%:budget%` points; the reconcile applies a change | the worker's own curve |
| `up.pace_claude`, `up.pace_codex` | a curve for that provider's windows only, overriding `up.pace` (an `auto` worker paces each provider on its own); the reconcile applies a change | `up.pace` |
| `schedule.active` | weekly active slots in host-local time, e.g. `"Thu 07:00 -> Sat 15:00"` (comma-separated for several); `tauceti-fleet schedule --install` adds a systemd user timer that runs `up` when a slot opens and `down --drain` when it closes, acting only at the boundaries | always on |
| `up.claude`, `up.codex` | Claude authors, and `auto` authors (Codex first, then Claude) | 2 and 2; 1 and 0 in pilot mode |
| `gate.mutations_per_hour`, `gate.reads_per_hour` | fleet-wide GitHub budgets, rolling hour; the reconcile after each round applies a change | 40 and 600 |
| `authoring.max_open_prs` | authors stop while the account has this many open PRs in scope; the reconcile applies a change | the worker's 8 |
| `authoring.fallback_max_open` | with nothing on the target list, authors work outside it only while at most this many PRs are open; the reconcile applies a change | the worker's 6 |
| `authoring.lookahead`, `authoring.lookahead_max_branches` | before authoring outside the list, prove a blocked item ahead of its in-flight supplier on a fork branch, ported when the supplier lands; at most this many branches at once (docs/operating.md) | `false`, 4 |
| `decide.enabled` | the decide stage, which rules on declined rounds (see docs/operating.md) | `true` |
| `decide.close`, `decide.max_closes_per_day` | let the decide stage close the account's own PRs that main has subsumed, and how many a day | `false`, 3 |
| `models.claude`, `models.claude_effort` | the Claude model for every Claude round; the reconcile applies a change | `claude-opus-5-5`, `high` |
| `progress.enabled` | the progress-report worker `<name>-prog1` (see docs/operating.md); it publishes to TauCetiRoadmap, so it is off until you turn it on | `false` |
| `progress.repo`, `progress.ref`, `progress.strategy` | which TauCetiProgress it runs, and how it picks a roadmap | the worker's pinned upstream; `threshold` |
| `progress.threshold`, `progress.max_open` | the N + T a roadmap must exceed, and how many of its reports may be open at once | 10, 2 |

A flag of `up` overrides the matching setting for that run. For one-off runs the environment
overrides settings too: `TAUCETI_FLEET_NAME`, `TAUCETI_FLEET_TARGETS`, `TAUCETI_EXPECT_LOGIN`,
`TAUCETI_FLEET_WORKER`, `TAUCETI_FLEET_ROADMAP`, `CLAIM_REPO`, `TAUCETI_PACE`,
`TAUCETI_GATE_MUTATIONS_PER_HOUR`, `TAUCETI_GATE_READS_PER_HOUR`. `TAUCETI_FLEET_PYTHON` names an
interpreter that has `rich`, for the live view.

## Commands

| command | what it does |
|---|---|
| `init` | write the settings file |
| `up` | write `workers.toml`, pre-seed checkouts, start the manager, open the live view |
| `watch`, `status` | the live view, or one snapshot of it |
| `logins` | the Claude login pool: chains, leases, sign-ins still missing |
| `attention [--ack PR\|all] [--lookup]` | what needs you: rounds whose agent declined to act (a PR to close?), capped review exchanges |
| `targets [--apply]` | audit the list's in-flight items against their PRs |
| `periodic [--now STAGE]` | the cadenced curate and decide rounds |
| `restart ID… [--when-idle] [--force]` | restart workers between rounds |
| `reconcile [--dry-run]` | reshape the fleet from the backlog now (it runs after every round anyway) |
| `round` | one supervised round in the foreground, then the gate report |
| `logs ID [-f]` | one worker's log |
| `gate …` | the worker's gate commands: `status`, `report`, `publication prune`, … |
| `clear-halt` | show each halted worker's incident, then clear it |
| `warm-pool` | fill the Mathlib cache pool by hand |
| `down` | stop the manager and its workers |

## Requirements

- **TauCetiWorker**, branch `feat/roadmap-targets-v2` of
  [roed-math/TauCetiWorker](https://github.com/roed-math/TauCetiWorker). Target lists, the GitHub
  gate, the curate stage, and the sandbox fixes the fleet relies on are there and not yet upstream.
- **bubble** with fixes not yet upstream. Branch `fleet` of
  [roed-math/bubble](https://github.com/roed-math/bubble) combines them: five open upstream
  (kim-em/bubble#340 to #344), and two that let bubble run for a user confined by `incus-user`
  rather than root-equivalent `incus-admin` (docs/setup.md, section 2). Without #342 the sandbox's
  cache proxy wedges after 256 connections; without #343 reviews of PRs with more than 100 comments
  fail; without #344 the auth proxy goes deaf whenever Incus restarts (an unattended upgrade will do
  it) until it is restarted by hand.
- **Claude Code** 2.1.280 or newer for Opus 5.5, on the host and inside bubble's images (the `fleet`
  branch pins it). **Codex** is optional; without it the `auto` workers run on Claude.
- **A GitHub account for the fleet**, used by no person. [docs/setup.md](docs/setup.md) explains why.
