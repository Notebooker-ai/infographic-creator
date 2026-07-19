"""infographic-creator: an Open Notebook creator that turns notebook content into
a rich, illustrated infographic. The LLM designs it as an AntV Infographic DSL
string (emitted as ``infographic.v2``, rendered client-side to SVG by the
``@antv/infographic`` engine). It can produce any AntV template family —
list/sequence/compare/hierarchy/relation *and* ``chart-*`` charts — with the
family chosen automatically ("auto") or pinned via the ``kind`` config. Auto uses
a two-phase design: a cheap first pass analyses the content's shape and picks the
best-fitting template, then a second pass fills it. Earlier versions emitted
``infographic.v1`` stat/text/list/quote cards.
"""

import json
import re
from importlib import resources
from typing import ClassVar, Literal, Optional

from ai_prompter import Prompter
from loguru import logger
from open_notebook_creator_sdk import (
    BaseCreator,
    CreationError,
    CreationRequest,
    CreationResult,
    CreatorManifest,
    CreatorView,
    ModelRoleSpec,
)
from open_notebook_creator_sdk.schemas import InfographicV2
from pydantic import BaseModel, Field

__version__ = "0.5.0"

# AntV Infographic gallery — browsable catalog of every template/chart type.
GALLERY_URL = "https://infographic.antv.vision/gallery"

# Each infographic ``kind`` maps to the AntV template-name prefixes it may use.
# "auto" allows everything; the two-phase selector then picks within these.
KIND_FAMILIES: dict[str, list[str]] = {
    "auto": [
        "list-",
        "sequence-",
        "compare-",
        "hierarchy-",
        "relation-",
        "chart-",
    ],
    "list": ["list-"],
    "timeline": ["sequence-"],  # covers sequence-* and sequence-interaction-*
    "comparison": ["compare-"],
    "hierarchy": ["hierarchy-"],
    "flow": ["relation-"],
    "chart": ["chart-"],
}

# Human-readable hint per kind for the selector prompt (auto omitted — no constraint).
KIND_HINT: dict[str, str] = {
    "list": "list-*",
    "timeline": "sequence-* or sequence-interaction-*",
    "comparison": "compare-*",
    "hierarchy": "hierarchy-*",
    "flow": "relation-*",
    "chart": "chart-*",
}


class InfographicsConfig(BaseModel):
    # Which kind of infographic to build. "auto" lets the model analyse the
    # content shape and pick the best-fitting template family; any other value
    # pins generation to that family (see KIND_FAMILIES). "chart" produces an
    # AntV chart (line/bar/column/pie/wordcloud).
    kind: Literal[
        "auto", "list", "timeline", "comparison", "hierarchy", "flow", "chart"
    ] = Field(
        default="auto",
        title="Type",
        description="What kind of infographic to create.",
        json_schema_extra={
            "x-help-url": GALLERY_URL,
            "x-help-label": "View chart types",
        },
    )
    # AntV Infographic theme applied client-side. "auto" follows the app's
    # light/dark mode; "hand-drawn" is a sketchy preset. The DSL's own palette
    # still layers colour on top of the base theme.
    theme: Literal["auto", "light", "dark", "hand-drawn"] = Field(
        default="auto", description="Infographic theme"
    )
    count: int = Field(
        default=1,
        ge=1,
        le=6,
        title="Number to generate",
        description="How many to generate; each one uses a different design and emphasis.",
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def _valid_spec(spec: object) -> bool:
    """A usable AntV Infographic DSL: a non-empty string whose first non-blank
    line starts with ``infographic ``. The DSL itself is the contract; we keep
    validation loose so new AntV templates need no code change."""
    if not isinstance(spec, str):
        return False
    for line in spec.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.startswith("infographic ")
    return False


def _spec_template(spec: object) -> Optional[str]:
    """The template name from a spec's first line (``infographic <template>``)."""
    if not isinstance(spec, str):
        return None
    for line in spec.splitlines():
        stripped = line.strip()
        if stripped:
            parts = stripped.split()
            return parts[1] if len(parts) >= 2 and parts[0] == "infographic" else None
    return None


class InfographicCreator(BaseCreator):
    config_model: ClassVar[type] = InfographicsConfig

    @property
    def manifest(self) -> CreatorManifest:
        return self.build_manifest(
            key="infographics",
            name="Infographics",
            version=__version__,
            description="LLM-designed AntV infographic of the key story in the content.",
            sdk_compat=">=0.4,<1",
            emits=["infographic.v2"],
            model_roles=[
                ModelRoleSpec(
                    key="text",
                    kind="language",
                    requires=["structured_json"],
                    description="LLM that designs the infographic.",
                )
            ],
            icon="layout-dashboard",
            view=CreatorView(entry="view/index.html"),
        )

    async def _select_template(
        self,
        role,
        request: CreationRequest,
        antv_syntax: str,
        kind: str,
        prompts,
    ) -> Optional[str]:
        """Phase 1: analyse the content's shape and pick the single best-fitting
        template. Returns a validated template name, or ``None`` to let phase 2
        decide (on any failure, or when the pick falls outside the allowed
        family). Kept non-fatal so a hiccup here never blocks generation."""
        allowed_prefixes = KIND_FAMILIES.get(kind, KIND_FAMILIES["auto"])
        try:
            select_tmpl = prompts.joinpath("select.jinja").read_text()
            prompt = Prompter(template_text=select_tmpl).render(
                {
                    "content": request.content.text,
                    "antv_syntax": antv_syntax,
                    "instructions": request.instructions,
                    "kind": kind,
                    "kind_hint": KIND_HINT.get(kind),
                }
            )
            llm = role.create_language(structured={"type": "json"}, max_tokens=500)
            resp = await llm.ainvoke(prompt)
            raw = resp.content if hasattr(resp, "content") else str(resp)
            parsed = json.loads(_strip_fences(raw))
            template = parsed.get("template") if isinstance(parsed, dict) else None
            if isinstance(template, str):
                template = template.strip()
                if any(template.startswith(p) for p in allowed_prefixes):
                    logger.info(
                        f"infographics: selected template '{template}' "
                        f"(kind={kind}, reason={parsed.get('reason')!r})"
                    )
                    return template
                logger.warning(
                    f"infographics: selector picked '{template}' outside kind "
                    f"'{kind}'; letting phase 2 choose"
                )
        except Exception as e:  # selection is best-effort; never fatal
            logger.warning(f"infographics: template selection failed ({e}); "
                           "letting phase 2 choose")
        return None

    async def generate(self, request: CreationRequest) -> CreationResult:
        cfg = InfographicsConfig.model_validate(request.config)
        role = request.models.get("text")
        if role is None:
            return CreationResult(
                status="FAILURE",
                schema_id="infographic.v2",
                data={},
                errors=[CreationError(phase="setup", message="missing 'text' model role")],
                user_message="No language model was provided for infographic generation.",
            )

        prompts = resources.files("infographic_creator.prompts")
        antv_syntax = prompts.joinpath("antv_syntax.md").read_text()

        # Phase 1: pick the template (best-effort; None => phase 2 decides).
        chosen = await self._select_template(role, request, antv_syntax, cfg.kind, prompts)

        # Phase 2: design the infographic, using the chosen template if any.
        template = prompts.joinpath("infographic.jinja").read_text()
        prompt = Prompter(template_text=template).render(
            {
                "content": request.content.text,
                "antv_syntax": antv_syntax,
                "instructions": request.instructions,
                "kind": cfg.kind,
                "kind_hint": KIND_HINT.get(cfg.kind),
                "template": chosen,
            }
        )
        llm = role.create_language(structured={"type": "json"}, max_tokens=6000)
        resp = await llm.ainvoke(prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        try:
            parsed = json.loads(_strip_fences(raw))
        except json.JSONDecodeError as e:
            logger.error(f"infographics: non-JSON response: {e}")
            return CreationResult(
                status="FAILURE",
                schema_id="infographic.v2",
                data={},
                errors=[CreationError(phase="parse", message=f"invalid JSON: {e}", retryable=True)],
                user_message="The model returned an unparseable response. Please retry.",
            )

        spec = parsed.get("spec") if isinstance(parsed, dict) else None
        if not _valid_spec(spec):
            return CreationResult(
                status="FAILURE",
                schema_id="infographic.v2",
                data={},
                errors=[CreationError(phase="generate", message="no valid infographic spec", retryable=True)],
                user_message="No infographic could be generated from this content.",
            )

        # Non-fatal: note if the emitted template drifted outside the pinned kind.
        emitted = _spec_template(spec)
        if cfg.kind != "auto" and emitted is not None:
            allowed = KIND_FAMILIES.get(cfg.kind, [])
            if not any(emitted.startswith(p) for p in allowed):
                logger.warning(
                    f"infographics: emitted '{emitted}' outside pinned kind "
                    f"'{cfg.kind}'"
                )

        title = parsed.get("title")
        data = InfographicV2(
            title=title if isinstance(title, str) and title.strip() else None,
            spec=spec.strip(),
            theme=cfg.theme,
        ).model_dump()

        return CreationResult(
            status="SUCCESS",
            schema_id="infographic.v2",
            data=data,
        )
