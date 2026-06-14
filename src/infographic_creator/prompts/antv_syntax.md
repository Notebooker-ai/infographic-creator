AntV Infographic DSL — syntax & template catalog (non-chart templates).
Adapted from AntV Infographic's `infographic-creator` skill (MIT, v0.2.x,
https://github.com/antvis/Infographic). Refresh via AntV's `infographic-template-updater` skill.

## Grammar

- The first line must be `infographic <template-name>`.
- Then a `data` block, and an optional `theme` block. Inside a block, indent with TWO spaces per level.
- Key/value pairs are written `key value`. Arrays use `-` to start each object item.
- Put exactly ONE main data field that matches the template family (do not mix `lists`/`sequences`/`compares`/`root`/`nodes`/`items`).
- `title` and `desc` are optional top-level data fields.
- `value` should be a bare number; put units in `label` or `desc`.

### Icons (use them — they make infographics graphic)

- Add an `icon` to every meaningful item (list items, steps, nodes, compare items). Do not skip it just because it is optional.
- Prefer a short semantic phrase with SPACES, not hyphens: `rocket launch`, `shield check`, `chart line`, `users`, `database`. Never `rocket-launch`.
- Only omit `icon` for pure numeric/series data points.

### Theme (optional)

```
theme
  palette #3b82f6 #8b5cf6 #f97316
```

- `palette` colours are bare hex values — no quotes, no commas.
- The host applies a light/dark base theme automatically; the palette adds colour on top.

## Main data field by family

- `list-*` → `lists`
- `sequence-*` → `sequences` (optional `order asc|desc`)
- `sequence-interaction-*` → `sequences` (swim-lanes; each lane needs `label` and `children`; each child needs `label`, optional `id`/`icon`/`step`/`desc`) + `relations`
- `compare-binary-*` / `compare-hierarchy-left-right-*` → `compares` with EXACTLY two root nodes, each with its own `children` (every child has `label`)
- `compare-swot` → `compares` with multiple roots, each with optional `children`
- `compare-quadrant-*` / `quadrant-*` → `compares` with 4 quadrant roots
- `hierarchy-structure` → `items`
- other `hierarchy-*` (tree / mindmap) → a single `root`, nested recursively via `children`
- `relation-*` → `nodes` + `relations` (arrow syntax: `nodeId - label -> otherId`)
- fall back to `items` only when nothing else fits

## Template selection guide

- Ordered steps / phases / progression → `sequence-*`
- Multi-actor or multi-system interaction → `sequence-interaction-*`
- Parallel bullet points / key takeaways → `list-row-*` / `list-column-*` / `list-grid-*`
- Two-sided / before-after / option comparison → `compare-binary-*`
- SWOT → `compare-swot`; quadrant / prioritization → `compare-quadrant-*`
- Org chart / tree → `hierarchy-tree-*`; mind map → `hierarchy-mindmap-*`
- Node relationships / process dependencies → `relation-*`

## Available templates (pick the best fit)

lists: list-row-horizontal-icon-arrow, list-column-simple-vertical-arrow, list-column-vertical-icon-arrow, list-column-done-list, list-grid-badge-card, list-grid-candy-card-lite, list-grid-ribbon-card, list-sector-plain-text, list-waterfall-badge-card, list-waterfall-compact-card, list-zigzag-down-simple, list-zigzag-down-compact-card, list-zigzag-up-simple, list-zigzag-up-compact-card

sequences: sequence-ascending-steps, sequence-ascending-stairs-3d-underline-text, sequence-circular-simple, sequence-color-snake-steps-horizontal-icon-line, sequence-cylinders-3d-simple, sequence-filter-mesh-simple, sequence-funnel-simple, sequence-horizontal-zigzag-underline-text, sequence-mountain-underline-text, sequence-pyramid-simple, sequence-roadmap-vertical-simple, sequence-roadmap-vertical-plain-text, sequence-snake-steps-simple, sequence-snake-steps-compact-card, sequence-snake-steps-underline-text, sequence-stairs-front-compact-card, sequence-stairs-front-pill-badge, sequence-timeline-simple, sequence-timeline-rounded-rect-node, sequence-zigzag-pucks-3d-simple, sequence-zigzag-steps-underline-text

sequence-interaction: sequence-interaction-default-badge-card, sequence-interaction-default-animated-badge-card, sequence-interaction-default-compact-card, sequence-interaction-default-capsule-item, sequence-interaction-default-rounded-rect-node

compare: compare-binary-horizontal-badge-card-arrow, compare-binary-horizontal-simple-fold, compare-binary-horizontal-underline-text-vs, compare-hierarchy-left-right-circle-node-pill-badge, compare-quadrant-quarter-circular, compare-quadrant-quarter-simple-card, compare-swot

hierarchy: hierarchy-structure, hierarchy-tree-curved-line-rounded-rect-node, hierarchy-tree-tech-style-badge-card, hierarchy-tree-tech-style-capsule-item, hierarchy-mindmap-branch-gradient-capsule-item, hierarchy-mindmap-level-gradient-compact-card

relation: relation-dagre-flow-tb-badge-card, relation-dagre-flow-tb-animated-badge-card, relation-dagre-flow-tb-simple-circle-node, relation-dagre-flow-tb-animated-simple-circle-node

## Worked examples

list:
```
infographic list-row-horizontal-icon-arrow
data
  title Product growth focus
  desc Acquisition, conversion, retention
  lists
    - label Acquire
      desc Multi-channel outreach
      icon rocket launch
    - label Convert
      desc Streamline the path
      icon chart line
    - label Retain
      desc Loyalty and tiers
      icon repeat
theme
  palette #3b82f6 #8b5cf6 #f97316
```

sequence:
```
infographic sequence-ascending-steps
data
  title Release process
  sequences
    - label Confirm scope
      icon clipboard check
    - label Build
      icon code
    - label Ship
      icon rocket
  order asc
```

compare-swot:
```
infographic compare-swot
data
  title Product SWOT
  compares
    - label Strengths
      icon trophy
      children
        - label High brand awareness
          icon star
    - label Weaknesses
      icon alert circle
      children
        - label Cost pressure
          icon wallet
```

hierarchy:
```
infographic hierarchy-tree-curved-line-rounded-rect-node
data
  title Org structure
  root
    label Company
    icon building
    children
      - label Product
        icon layers
      - label Engineering
        icon code
```

relation:
```
infographic relation-dagre-flow-tb-simple-circle-node
data
  title System relations
  nodes
    - label API
    - id db
      label DB
  relations
    API - read/write -> db
```

## Self-check before output

- First line is `infographic <template-name>`.
- Exactly one main data field, matching the template family.
- Every meaningful item has an `icon` (semantic phrase, spaces not hyphens).
- `palette` values are bare hex (no quotes/commas).
- `compare-binary-*` has exactly two roots, each with `children`; every child has `label`.
