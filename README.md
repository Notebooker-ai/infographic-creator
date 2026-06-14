# infographic-creator

An [Open Notebook](https://open-notebook.ai) **creator** plugin: turns notebook
content into a composed **infographic** — a themed poster of key-stat cards,
insight text, bulleted takeaways, and quotes.

- Emits the `infographic.v1` artifact schema (rendered client-side; PNG/SVG export).
- No charts — data charts live in [`chart-creator`](https://github.com/Notebooker-ai/chart-creator) (`chart_spec.v1`).
- Implements the [`open-notebook-creator-sdk`](https://github.com/Notebooker-ai/open-notebook-creator-sdk) `BaseCreator` contract; registers under `open_notebook.creators`.

## Model roles

| role | kind | requires |
|------|------|----------|
| `text` | language | `structured_json` |

## Config

| field | default | notes |
|-------|---------|-------|
| `max_blocks` | 8 | 1–20 |
| `theme` | "auto" | auto/light/dark |

## Dev

```bash
uv sync --extra dev
uv run pytest
```

MIT licensed.
