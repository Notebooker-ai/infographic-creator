"""Tests for InfographicCreator (infographic.v2 / AntV DSL) with a stubbed model."""

from __future__ import annotations

import json
import tempfile

import pytest
from infographic_creator import InfographicCreator
from open_notebook_creator_sdk import ContentBundle, CreationRequest, ModelRole
from open_notebook_creator_sdk.testing import (
    assert_creator_compliant,
    assert_result_compliant,
)

_SPEC = (
    "infographic list-row-horizontal-icon-arrow\n"
    "data\n"
    "  title Product growth\n"
    "  lists\n"
    "    - label Acquire\n"
    "      icon rocket\n"
    "    - label Retain\n"
    "      icon repeat\n"
)


class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def __init__(self, payload):
        self._payload = payload

    async def ainvoke(self, _):
        return _FakeResp(self._payload)


class _FakeRole(ModelRole):
    payload: str = ""

    def create_language(self, **_):
        return _FakeLLM(self.payload)


def _role(obj):
    return _FakeRole(provider="f", model="f", payload=json.dumps(obj))


def test_static_compliance():
    assert_creator_compliant(InfographicCreator())


@pytest.mark.asyncio
async def test_generate_infographic():
    creator = InfographicCreator()
    payload = {"title": "Climate Snapshot", "spec": _SPEC}
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="some content"),
            config={"theme": "auto"},
            models={"text": _role(payload)},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "SUCCESS"
        assert_result_compliant(creator, result)
        assert result.schema_id == "infographic.v2"
        assert result.data["title"] == "Climate Snapshot"
        assert result.data["spec"].startswith("infographic ")
        assert result.data["library"] == "antv-infographic"
        assert result.data["theme"] == "auto"


@pytest.mark.asyncio
async def test_failure_when_spec_invalid():
    creator = InfographicCreator()
    # spec does not start with "infographic "
    payload = {"title": "T", "spec": "data\n  lists\n    - label x"}
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="x"),
            models={"text": _role(payload)},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "FAILURE"


@pytest.mark.asyncio
async def test_failure_when_spec_missing():
    creator = InfographicCreator()
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="x"),
            models={"text": _role({"title": "T"})},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "FAILURE"


@pytest.mark.asyncio
async def test_no_text_role_is_failure():
    creator = InfographicCreator()
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(content=ContentBundle(text="x"), output_dir=td, artifact_id="a")
        result = await creator.generate(req)
        assert result.status == "FAILURE"
        assert result.errors[0].phase == "setup"


@pytest.mark.asyncio
async def test_strips_markdown_fences():
    creator = InfographicCreator()
    obj = {"title": "T", "spec": _SPEC}
    fenced = "```json\n" + json.dumps(obj) + "\n```"
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="x"),
            models={"text": _FakeRole(provider="f", model="f", payload=fenced)},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "SUCCESS"
        assert result.data["title"] == "T"


def test_manifest_declares_view_bundle_and_it_ships():
    """The creator owns its UI: the manifest points at a shipped HTML view bundle
    that is self-contained (offline) and renders every schema we've emitted."""
    from importlib import resources

    m = InfographicCreator().manifest
    assert m.view is not None
    assert m.view.entry == "view/index.html"
    asset = resources.files("infographic_creator").joinpath(m.view.entry)
    assert asset.is_file()
    html = asset.read_text()
    # self-contained + speaks the host handshake + dispatches both schemas
    assert "open-notebook:ready" in html
    assert "open-notebook:artifact" in html
    assert "infographic.v2" in html
    assert "infographic.v1" in html
    # inline <script> blocks are fine; what must NOT appear is any external fetch.
    assert 'src="http' not in html
