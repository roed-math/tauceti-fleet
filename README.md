# tauceti-fleet

Run a fleet of [TauCetiWorker](https://github.com/kim-em/TauCetiWorker) workers against
[Tau Ceti](https://github.com/TauCetiProject/TauCeti), aimed at one goal: an **operator target list**
of roadmap milestones you want proved. The fleet authors PRs for those milestones, fixes and rebases
its own PRs, reviews other people's PRs in return, and keeps the target list true as work lands.

One command, `tauceti-fleet`, shapes the fleet from the backlog, drives the worker's own manager,
keeps a pool of Claude logins that renew themselves, runs everything through a shared GitHub
budget, and shows a live view.

```
bin/tauceti-fleet     the tool
targets/              target lists; each fleet points at one of them
docs/setup.md         installing a host, and each user on it
docs/operating.md     what the fleet does on its own, and what needs you
docs/target-lists.md  writing a target list
```

Everything about one particular fleet lives in its **settings file**, outside this repository. The
only fleet-specific files here are the target lists.

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
| `fleet.targets` | the target list the authors work through | required |
| `fleet.github_login` | the GitHub account every worker must act as; any other identity halts the worker | required |
| `fleet.claim_repo` | the project-wide claim namespace; every fleet must agree on it | `TauCetiProject/tauceti-claims` |
| `paths.worker` | a TauCetiWorker checkout (see Requirements) | `~/TauCetiWorker-v2` |
| `paths.roadmap` | a TauCetiRoadmap checkout, to check the list's areas are real roadmaps | `~/TauCetiRoadmap` |
| `up.pilot` | start in pilot mode | `init` writes `true` |
| `up.sandbox` | `bubble` (egress-denied containers) or `host` | `init` writes `bubble` |
| `up.pace` | the worker's pacing curve, `time%:budget%` points | the worker's own curve |
| `up.claude`, `up.codex` | Claude authors, and `auto` authors (Codex first, then Claude) | 2 and 2; 1 and 0 in pilot mode |
| `gate.mutations_per_hour`, `gate.reads_per_hour` | fleet-wide GitHub budgets, rolling hour | 40 and 600 |
| `models.claude`, `models.claude_effort` | the Claude model for every Claude round | `claude-opus-5-5`, `high` |
| `progress.repo`, `progress.ref`, `progress.strategy` | which TauCetiProgress the progress rounds run, and how it picks a roadmap | the worker's pinned upstream |

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
| `periodic [--now STAGE] [--enable/--disable progress]` | the cadenced curate and progress rounds |
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
- **bubble** with four fixes still open upstream (kim-em/bubble#340, #341, #342, #343). Branch
  `fleet` of [roed-math/bubble](https://github.com/roed-math/bubble) combines them. Without #342 the
  sandbox's cache proxy wedges after 256 connections; without #343 reviews of PRs with more than 100
  comments fail.
- **Claude Code** 2.1.280 or newer for Opus 5.5, on the host and inside bubble's images (the `fleet`
  branch pins it). **Codex** is optional; without it the `auto` workers run on Claude.
- **A GitHub account for the fleet**, used by no person. [docs/setup.md](docs/setup.md) explains why.
