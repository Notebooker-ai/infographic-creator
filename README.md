# infographic-creator

An [Open Notebook](https://open-notebook.ai) **creator** plugin: turns notebook
content into a rich, illustrated **infographic**. The LLM designs it as an
[AntV Infographic](https://infographic.antv.vision/) DSL string, rendered
client-side to SVG by the `@antv/infographic` engine.

- Emits the `infographic.v2` artifact schema (rendered client-side; PNG/SVG export).
- Covers every AntV template family — list / sequence / compare / hierarchy / relation
  **and `chart-*` charts** (line / bar / column / pie / wordcloud). Pick one with the
  **Type** dropdown, or leave it on **Auto**.
- **Smarter Auto**: a two-phase design — a cheap first pass analyses the content's shape
  and picks the best-fitting template, then a second pass fills it — so different content
  yields different layouts instead of always defaulting to the same one.
- Implements the [`open-notebook-creator-sdk`](https://github.com/Notebooker-ai/open-notebook-creator-sdk) `BaseCreator` contract; registers under `open_notebook.creators`.

## Model roles

| role | kind | requires |
|------|------|----------|
| `text` | language | `structured_json` |

## Config

| field | default | notes |
|-------|---------|-------|
| `kind` | "auto" | Type of infographic: auto / list / timeline / comparison / hierarchy / flow / chart. Links to the [AntV gallery](https://infographic.antv.vision/gallery). |
| `theme` | "auto" | auto/light/dark/hand-drawn (AntV theme) |
| `count` | 1 | How many to generate (1–6); each uses a different design. |

## Dev

```bash
uv sync --extra dev
uv run pytest
```

MIT licensed.
