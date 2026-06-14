"""Tests for InfographicCreator (infographic.v1) with a stubbed model (no network)."""

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
    payload = {
        "title": "Climate Snapshot",
        "subtitle": "Key figures",
        "blocks": [
            {"type": "stat", "value": "1.5°C", "label": "Warming target", "icon": "thermometer"},
            {"type": "text", "heading": "Why it matters", "body": "Crossing it raises risk."},
            {"type": "list", "heading": "Drivers", "items": ["energy", "transport"]},
            {"type": "quote", "text": "Act now.", "attribution": "IPCC"},
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="some content"),
            config={"max_blocks": 8},
            models={"text": _role(payload)},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "SUCCESS"
        assert_result_compliant(creator, result)
        assert result.data["title"] == "Climate Snapshot"
        assert len(result.data["blocks"]) == 4


@pytest.mark.asyncio
async def test_partial_on_some_invalid_blocks():
    creator = InfographicCreator()
    payload = {
        "title": "Mixed",
        "blocks": [
            {"type": "stat", "value": "10", "label": "ok"},
            {"type": "bogus", "value": "x"},          # invalid type
            {"type": "text"},                          # missing body
            {"type": "list", "items": []},             # empty items
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="x"),
            models={"text": _role(payload)},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "PARTIAL"
        assert len(result.data["blocks"]) == 1
        assert result.warnings


@pytest.mark.asyncio
async def test_respects_max_blocks():
    creator = InfographicCreator()
    blocks = [{"type": "stat", "value": str(i), "label": f"s{i}"} for i in range(10)]
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="x"),
            config={"max_blocks": 3},
            models={"text": _role({"title": "T", "blocks": blocks})},
            output_dir=td,
            artifact_id="a",
        )
        result = await creator.generate(req)
        assert result.status == "SUCCESS"
        assert len(result.data["blocks"]) == 3


@pytest.mark.asyncio
async def test_failure_when_no_usable_blocks():
    creator = InfographicCreator()
    with tempfile.TemporaryDirectory() as td:
        req = CreationRequest(
            content=ContentBundle(text="x"),
            models={"text": _role({"title": "T", "blocks": [{"type": "bogus"}]})},
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
    obj = {"title": "T", "blocks": [{"type": "stat", "value": "1", "label": "x"}]}
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
