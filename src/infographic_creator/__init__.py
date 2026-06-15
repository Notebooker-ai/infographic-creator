"""infographic-creator: an Open Notebook creator that turns notebook content into
a rich, illustrated infographic. The LLM designs it as an AntV Infographic DSL
string (emitted as ``infographic.v2``, rendered client-side to SVG by the
``@antv/infographic`` engine). This creator uses the non-chart templates
(sequence/list/compare/hierarchy/relation); ``chart-*`` templates are produced by
chart-creator. Earlier versions emitted ``infographic.v1`` stat/text/list/quote cards.
"""

import json
import re
from importlib import resources
from typing import ClassVar, Literal

from ai_prompter import Prompter
from loguru import logger
from open_notebook_creator_sdk import (
    BaseCreator,
    CreationError,
    CreationRequest,
    CreationResult,
    CreatorManifest,
    ModelRoleSpec,
)
from open_notebook_creator_sdk.schemas import InfographicV2
from pydantic import BaseModel, Field

__version__ = "0.3.1"


class InfographicsConfig(BaseModel):
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


class InfographicCreator(BaseCreator):
    config_model: ClassVar[type] = InfographicsConfig

    @property
    def manifest(self) -> CreatorManifest:
        return self.build_manifest(
            key="infographics",
            name="Infographics",
            version=__version__,
            description="LLM-designed AntV infographic of the key story in the content.",
            sdk_compat=">=0.2,<1",
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
        )

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
        template = prompts.joinpath("infographic.jinja").read_text()
        antv_syntax = prompts.joinpath("antv_syntax.md").read_text()
        prompt = Prompter(template_text=template).render(
            {
                "content": request.content.text,
                "antv_syntax": antv_syntax,
                "instructions": request.instructions,
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
