# Troubleshooting

Symptoms a fleet has actually shown, what caused each, and the fix. Most of them point at the wrong
thing in their first log line, so the cause is worth reading even when the symptom looks familiar.

## Where to look

- `tauceti-fleet status` (or `watch`): each worker's health and phase, the subscription usage left,
  the gate, the Mathlib pool and what needs you.
- `tauceti-fleet logs ID -f`: one worker's log. Each round's agent transcript is beside it under
  `state/logs/<id>/` in the fleet home.
- `tauceti-fleet attention`: everything the fleet is waiting on you for.
- `tauceti-fleet gate report --since 24h`: every GitHub request, admitted or refused.
- `watchdog.log` in the fleet home: the daemons the reconcile restarted, and why.
- bubble's own logs, `~/.bubble/auth-proxy.log` and `~/.bubble/artifact-cache.log`, and `incus list`.

## Workers idle

**Every worker `waiting-quota`, "weekly exhausted".** The subscription's weekly allowance is spent.
The `usage` row shows what is left in each window and when it resets. Nothing is wrong; the workers
resume by themselves. Another Claude subscription, or Codex for the `auto` workers, adds capacity.

**Authors idle with "no open targets … eligible".** Either the list's in-flight items are stale (a
PR closed rather than merged, so everything that needs it waits), or every open item waits on a
prerequisite. `tauceti-fleet targets` audits the in-flight items, and the curator fixes the
unambiguous ones every 6 hours. When the list has nothing to offer, authors work outside it while the
account has at most `authoring.fallback_max_open` open PRs.

**Authors disabled although the list has work.** The account has `authoring.max_open_prs` open PRs
or more, so the reconcile turned the authors off until fixes and merges bring the count down.

**A worker halted.** It saw an identity other than `fleet.github_login`, or a credential error.
`tauceti-fleet clear-halt` shows the incident and clears it once you have looked.

## Rounds fail or hang

**A Claude round fails with "401 OAuth access token has been revoked", just after another worker
logged "access token renewed".** The two workers share a login chain, and renewing a Claude token
revokes the old one. `tauceti-fleet logins` lists the chains still to sign in; every Claude-capable
worker should hold its own.

**Rounds hang in `lake cache get`; workers say "running" but use no CPU.** bubble's artifact cache
has wedged: bubble without kim-em/bubble#342 leaks a connection slot per request and stops
answering after 256. `ss -tanp` shows connections to the cache's port that no process owns. Install
bubble from the `fleet` branch (README, Requirements). Until then the reconcile restarts a cache that
looks wedged and notes it in `watchdog.log`.

**Every sandboxed round fails to fetch or push, with a refused connection to the bridge address
(`10.x.x.1:7654`), typically after an unattended upgrade.** bubble's auth proxy is bound to the
network interface Incus had when the proxy started, and restarting Incus rebuilds it. Without
kim-em/bubble#344 the proxy stays alive and deaf. The reconcile restarts a proxy that does not
answer; by hand, `systemctl --user restart bubble-auth-proxy.service`.

**A review fails three times on one PR, "needs infrastructure repair".** On a PR with more than 100
review comments, `gh` follows GitHub's pagination to a `/repositories/<id>/…` URL, which bubble's
auth proxy refused without kim-em/bubble#343.

**A fixer "running" for hours after a merge, building modules its PR never touched.** The merge
brought in a newer `main` whose TauCeti build outputs the round did not fetch, so it rebuilt them.
Current worker prompts fetch them after merging; update the worker checkout.

**"gh pr list failed (GitHub API?)".** GitHub timed out (HTTP 504) on a large query. It is transient,
and the worker splits the query and retries.

**Every sandboxed round fails within a minute: Lake cannot fetch Mathlib, "Repository mismatch:
leanprover-community/mathlib4 != TauCetiProject/TauCeti".** The first lines of the round's agent log
say why: "host uid … not mapped", then "dubious ownership" for each Lake dependency bubble tried to
pre-populate. Root has not delegated this user's ids to Incus, so the shared git store mounted into
the container belongs to nobody there. See docs/setup.md, section 2; `up` refuses to start without it.

## Pushes and commits

**Pushes refused with a message about workflows.** The GitHub token lacks the `workflow` scope, and
any branch based on a `main` that changed a workflow file needs it:
`gh auth refresh -h github.com -s workflow`.

**"Committer identity unknown" in every agent transcript.** The fleet user has no global git
identity, and the containers inherit it (docs/setup.md, section 3).

**A fixer's push is refused as "stale info", though the fork's branch has the new commit.** GitHub
did not update the PR's head after an earlier push. Compare `git ls-remote` of the branch with
`gh pr view N --json headRefOid`; any new push to the branch brings the PR back in step.

**The curator's changes are never committed or pushed.** The log says why. "git refuses …" means the
list is in a repository another user owns, which this user must mark as a safe.directory
(docs/setup.md, "Sharing one target list"); `up` checks this before it starts. "push … failed — the
commit stays local" means the fleet's account cannot push to the list's repository.

**`targets-diverged` under `attention`.** A curation committed here conflicts with one pushed from
elsewhere. See [target-lists.md](target-lists.md#sharing-a-list).

**`gate status` lists parked publications.** Rounds that failed before they published anything
leave a parked record with no effect on GitHub. `tauceti-fleet gate publication prune` archives them.

## Setting up

**The worker's preflight reports "missing uvx".** `~/.local/bin` is not on the PATH of the shell
that started the fleet. Log in again (uv's installer adds it to `~/.profile`) and restart.

**`PermissionError` under `/tmp/.cache/tauceti-agent-env` for the second fleet user on a host.** An
older worker kept per-round credential copies in one temp directory for every user. Update the
worker checkout.

**A second fleet's bubble cannot start its daemons, or its containers reach the first fleet's.** The
two users' bubbles use the same ports. Give every user after the first its own (docs/setup.md,
"Several fleets on one host").

**A "dry run" changed something.** Some did, in the past; `up --dry-run` copied worker checkouts
until 2026-10-01. Now it writes `workers.dry-run.toml` beside the real config, creates the gate
directory, and only reports the checkouts it would copy. Check what any dry run writes before you
trust it on a live host.
