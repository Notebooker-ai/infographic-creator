"""infographic-creator: an Open Notebook creator that turns notebook content into
a composed, designed infographic (emitted as ``infographic.v1``, rendered
client-side as themed stat/text/list/quote cards). Data charts live in
chart-creator (``chart_spec.v1``); infographics here contain no charts.
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
from open_notebook_creator_sdk.schemas import InfographicV1
from pydantic import BaseModel, Field

__version__ = "0.2.0"

_BLOCK_TYPES = {"stat", "text", "list", "quote"}
# Fields the renderer/schema understands per block (others are dropped).
_BLOCK_FIELDS = {
    "type",
    "value",
    "label",
    "description",
    "icon",
    "heading",
    "body",
    "items",
    "text",
    "attribution",
}


class InfographicsConfig(BaseModel):
    max_blocks: int = Field(
        default=8, ge=1, le=20, description="Maximum infographic blocks"
    )
    # Layout theme applied client-side; "auto" follows the app's light/dark mode.
    theme: Literal["auto", "light", "dark"] = Field(
        default="auto", description="Infographic theme"
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def _clean_block(block: object) -> dict | None:
    """Validate/normalize one block; return None if unusable."""
    if not isinstance(block, dict):
        return None
    btype = block.get("type")
    if btype not in _BLOCK_TYPES:
        return None
    cleaned = {k: v for k, v in block.items() if k in _BLOCK_FIELDS}
    # Require the minimum field(s) per type to be meaningful.
    if btype == "stat" and not (cleaned.get("value") or cleaned.get("label")):
        return None
    if btype == "text" and not cleaned.get("body"):
        return None
    if btype == "list" and not (isinstance(cleaned.get("items"), list) and cleaned["items"]):
        return None
    if btype == "quote" and not cleaned.get("text"):
        return None
    return cleaned


class InfographicCreator(BaseCreator):
    config_model: ClassVar[type] = InfographicsConfig

    @property
    def manifest(self) -> CreatorManifest:
        return self.build_manifest(
            key="infographics",
            name="Infographics",
            version=__version__,
            description="LLM-generated infographic of key stats, insights, and quotes.",
            sdk_compat=">=0.2,<1",
            emits=["infographic.v1"],
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
                schema_id="infographic.v1",
                data={},
                errors=[CreationError(phase="setup", message="missing 'text' model role")],
                user_message="No language model was provided for infographic generation.",
            )

        template = resources.files("infographic_creator.prompts").joinpath(
            "infographic.jinja"
        ).read_text()
        prompt = Prompter(template_text=template).render(
            {"content": request.content.text, "max_blocks": cfg.max_blocks}
        )
        llm = role.create_language(structured={"type": "json"}, max_tokens=4000)
        resp = await llm.ainvoke(prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        try:
            parsed = json.loads(_strip_fences(raw))
        except json.JSONDecodeError as e:
            logger.error(f"infographics: non-JSON response: {e}")
            return CreationResult(
                status="FAILURE",
                schema_id="infographic.v1",
                data={},
                errors=[CreationError(phase="parse", message=f"invalid JSON: {e}", retryable=True)],
                user_message="The model returned an unparseable response. Please retry.",
            )

        if not isinstance(parsed, dict):
            return CreationResult(
                status="FAILURE",
                schema_id="infographic.v1",
                data={},
                errors=[CreationError(phase="generate", message="response was not an object")],
                user_message="No infographic could be generated from this content.",
            )

        raw_blocks = parsed.get("blocks", []) if isinstance(parsed.get("blocks"), list) else []
        good = [b for b in (_clean_block(b) for b in raw_blocks) if b]
        dropped = len(raw_blocks) - len(good)
        good = good[: cfg.max_blocks]

        warnings: list[str] = []
        errors: list[CreationError] = []
        if dropped > 0:
            warnings.append(f"Dropped {dropped} invalid block(s).")
            errors.append(CreationError(phase="validate", message=f"{dropped} invalid blocks"))

        title = parsed.get("title")
        if not good or not isinstance(title, str) or not title.strip():
            return CreationResult(
                status="FAILURE",
                schema_id="infographic.v1",
                data={},
                warnings=warnings,
                errors=errors or [CreationError(phase="generate", message="no usable blocks/title")],
                user_message="No infographic could be generated from this content.",
            )

        data = InfographicV1(
            title=title,
            subtitle=parsed.get("subtitle") if isinstance(parsed.get("subtitle"), str) else None,
            blocks=good,
        ).model_dump()

        return CreationResult(
            status="PARTIAL" if errors else "SUCCESS",
            schema_id="infographic.v1",
            data=data,
            warnings=warnings,
            errors=errors,
        )
