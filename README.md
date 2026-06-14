# infographic-creator

An [Open Notebook](https://open-notebook.ai) **creator** plugin: turns notebook
content into a rich, illustrated **infographic**. The LLM designs it as an
[AntV Infographic](https://infographic.antv.vision/) DSL string, rendered
client-side to SVG by the `@antv/infographic` engine.

- Emits the `infographic.v2` artifact schema (rendered client-side; PNG/SVG export).
- Uses the non-chart templates (sequence / list / compare / hierarchy / relation);
  `chart-*` templates are produced by [`chart-creator`](https://github.com/Notebooker-ai/chart-creator) (also `infographic.v2`).
- Implements the [`open-notebook-creator-sdk`](https://github.com/Notebooker-ai/open-notebook-creator-sdk) `BaseCreator` contract; registers under `open_notebook.creators`.

## Model roles

| role | kind | requires |
|------|------|----------|
| `text` | language | `structured_json` |

## Config

| field | default | notes |
|-------|---------|-------|
| `theme` | "auto" | auto/light/dark/hand-drawn (AntV theme) |

## Dev

```bash
uv sync --extra dev
uv run pytest
```

MIT licensed.
