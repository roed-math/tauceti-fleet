# tauceti-fleet

The tooling and the target lists for fleets of [TauCetiWorker](https://github.com/kim-em/TauCetiWorker)
workers run by roed-math against [Tau Ceti](https://github.com/TauCetiProject/TauCeti).

- `bin/gq2-fleet` — the fleet wrapper: shapes the fleet from the backlog, drives the worker's manager,
  keeps the Claude login pool, the Mathlib cache pool and the GitHub gate, and shows the live view.
  Deployed on the fleet host by pulling this repository.
- `targets/` — operator target lists (`<!-- tauceti-targets:v1 -->` files) the authoring workers work
  through, one per fleet goal. `targets/gq2_axiom_targets.md` is the `G_{ℚ_2}` axiom programme. The
  fleet's curator keeps them true as PRs merge or close and as other people land the milestones.
