# Target lists

A target list tells the authors what to work on: the roadmap milestones on the path to one goal,
grouped by roadmap. The authors take only the items that are open and whose prerequisites have
landed, and the prompt names exactly those milestones. The file is re-read every round, so edits
take effect without a restart. `targets/` holds the lists in use; `fleet.targets` names the one a
fleet follows.

## Format

```markdown
# A goal
<!-- tauceti-targets:v1 -->
Free text until the first `## ` heading: the goal, the ordering rule, anything a reader needs.

## LocalFieldsRamification
- [ ] `ramification-index` — Layer 0, `e` and `f`: "Define …" (serves: B9; needs: `normalized-valuation`)
- [~] `unitfiltration` — Layer 1, the unit filtration (serves: B5; needs: none; in flight: #5500)
- [x] `normalized-valuation` — Layer 0, the normalized valuation (serves: B5; done: #5489)
> Note lines, and anything else that is not an item, are ignored.

## Gaps
Milestones no roadmap states yet. This section is never authored against.
```

- The marker comment is required. Without it the file is not a target list and the round stops
  rather than author against a misread file.
- Each `## ` heading is an **area**: the exact name of a roadmap directory in TauCetiRoadmap.
  `up` refuses a list naming an area that is not there. A drafted roadmap whose PR has not merged
  belongs under `## Gaps` until it does.
- An item is `- [ ]` open, `- [~]` in flight, or `- [x]` done. Its **slug** is the first backticked
  token, conventionally the milestone's main declaration in kebab-case. The text runs from ` — ` to
  the trailing parenthesis.
- The trailing parenthesis holds `key: value` clauses separated by `;`. `needs:` lists prerequisite
  slugs from any area, or `none`. `in flight: #N` names the PR working on the item. Anything else
  (`serves:`, `done:`) is kept verbatim for readers.
- An item is **eligible** when it is open and everything it needs is done; an in-flight prerequisite
  counts as not landed.

## Keeping it true

A list goes stale in two ways: a PR marked in flight is closed rather than merged, or someone else
lands the milestone. Either leaves the items that need it ineligible, and the authors idle.

The curator, the periodic `curate` round, fixes both, as described in
[operating.md](operating.md#the-periodic-rounds). `tauceti-fleet targets` shows the same audit of
in-flight items by hand, and `--apply` writes the unambiguous changes.

Mark an item `[~]` with `in flight: #N` when you open a PR for it by hand. The fleet's own authors
record their claims themselves, and the live view counts an item done as soon as a merged PR carries
its marker.

## Writing a good list

- Take milestones from what the roadmap READMEs actually state, not from what you wish they said.
  An item no roadmap describes cannot be reviewed against anything; it belongs under `## Gaps`, and
  the fix is a roadmap PR.
- Keep items small enough for one PR each, and write `needs:` honestly: the order the authors take
  items in comes from it.
- Say in the preamble what the goal is and what must not be done on the way (for example, no
  special-case shortcuts that prove only the instance you need).
