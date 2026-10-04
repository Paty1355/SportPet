import asyncio
import json
from io import BytesIO
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from openai import AsyncAzureOpenAI
from PIL import Image
from pydantic import ValidationError

from app.agents.vision.agent import (
    MachineNotRecognized,
    VisionAgent,
    VisionKnowledgeUnavailable,
    get_vision_agent,
)
from app.agents.vision.knowledge import GymMachineKnowledge
from app.agents.vision.llm import AzureVisionLLM, VisionModelResponseError
from app.agents.vision.prompts import USAGE_SYSTEM_PROMPT
from app.agents.vision.seed import load_machines, main
from app.core.config import settings
from app.main import app
from app.schemas.vision import MachineCatalogEntry, MachineDocument, MachineIdentification, MachineUsage


@pytest.fixture
def machine():
    return MachineDocument(
        machine_id="example_machine",
        name="Example machine",
        aliases=["example"],
        category="Example category",
        description="Opis z karty urządzenia.",
        primary_muscles=["Partia główna"],
        secondary_muscles=[],
        setup_steps=["Ustawienie ze źródła."],
        exercise_steps=["Wykonanie ze źródła."],
        tips=["Wskazówka ze źródła."],
        sources=["Example source"],
    )


class ControlledLLM:
    def __init__(self, machine_id="example_machine"):
        self.machine_id = machine_id
        self.calls = []

    async def identify(self, image, catalog):
        self.calls.append(("identify", image, catalog))
        return MachineIdentification(machine_id=self.machine_id, machine_name="Model-generated name")

    async def describe(self, machine_context):
        self.calls.append(("describe", machine_context))
        return MachineUsage.model_validate(machine_context.model_dump(include=set(MachineUsage.model_fields)))


@pytest.fixture
def vision_client(client, chroma, machine):
    knowledge = GymMachineKnowledge()
    knowledge.seed([machine])
    llm = ControlledLLM()
    app.dependency_overrides[get_vision_agent] = lambda: VisionAgent(llm, knowledge)
    yield client, llm


def test_knowledge_upsert_updates_card_without_duplicate(chroma, machine):
    knowledge = GymMachineKnowledge()
    knowledge.seed([machine])
    updated = machine.model_copy(update={"description": "Zaktualizowany opis."})
    knowledge.seed([updated])

    assert knowledge.count() == 1
    assert knowledge.search(machine.name, machine.machine_id).description == updated.description
    assert knowledge.get_catalog()[0].machine_id == machine.machine_id


def test_knowledge_retrieval_is_filtered_by_machine(chroma, machine):
    knowledge = GymMachineKnowledge()
    other = machine.model_copy(update={"machine_id": "other_machine", "sources": ["Other source"]})
    knowledge.seed([machine, other])

    assert knowledge.search(other.name, machine.machine_id).sources == machine.sources
    assert knowledge.search(machine.name, "missing_machine") is None


def test_knowledge_rejects_duplicate_ids_before_writing(chroma, machine):
    knowledge = GymMachineKnowledge()
    with pytest.raises(ValueError, match="unique"):
        knowledge.seed([machine, machine])
    assert knowledge.count() == 0


def test_endpoint_runs_full_pipeline_without_login(vision_client, machine):
    client, llm = vision_client
    output = BytesIO()
    Image.new("RGB", (16, 12), "green").save(output, format="PNG")
    image = output.getvalue()
    response = client.post("/api/v1/agents/vision/analyze", files={"file": ("machine.png", image, "image/png")})

    assert response.status_code == 200
    body = response.json()
    assert body["machine_id"] == machine.machine_id
    assert body["machine_name"] == machine.name
    assert body["category"] == machine.category
    assert body["sources"] == machine.sources
    assert body["exercise_steps"] == machine.exercise_steps
    assert [call[0] for call in llm.calls] == ["identify", "describe"]
    with Image.open(BytesIO(llm.calls[0][1])) as prepared:
        assert prepared.format == "JPEG"
        assert prepared.size == (16, 12)
    assert llm.calls[1][1] == machine


def test_empty_knowledge_skips_model_calls(chroma):
    llm = ControlledLLM()
    with pytest.raises(VisionKnowledgeUnavailable, match="empty"):
        asyncio.run(VisionAgent(llm, GymMachineKnowledge()).run(b"image"))
    assert llm.calls == []


@pytest.mark.parametrize("machine_id", [None, "not_in_catalog"])
def test_unknown_identification_does_not_generate_instructions(chroma, machine, machine_id):
    knowledge = GymMachineKnowledge()
    knowledge.seed([machine])
    llm = ControlledLLM(machine_id)
    with pytest.raises(MachineNotRecognized):
        asyncio.run(VisionAgent(llm, knowledge).run(b"image"))
    assert len(llm.calls) == 1


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (MachineNotRecognized("Unsupported machine"), 422),
        (VisionKnowledgeUnavailable("Empty knowledge"), 503),
        (VisionModelResponseError("Invalid response"), 502),
    ],
)
def test_endpoint_maps_agent_errors(client, error, status):
    class FailedAgent:
        async def run(self, image):
            raise error

    app.dependency_overrides[get_vision_agent] = FailedAgent
    output = BytesIO()
    Image.new("RGB", (16, 12), "green").save(output, format="PNG")
    response = client.post(
        "/api/v1/agents/vision/analyze", files={"file": ("machine.png", output.getvalue(), "image/png")}
    )
    assert response.status_code == status
    assert response.json()["detail"] == str(error)


def test_factory_without_credentials_returns_service_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "azure_openai_endpoint", None)
    monkeypatch.setattr(settings, "azure_openai_api_key", None)
    get_vision_agent.cache_clear()
    try:
        with pytest.raises(HTTPException) as exc:
            get_vision_agent()
        assert exc.value.status_code == 503
    finally:
        get_vision_agent.cache_clear()


def test_seed_dry_run_does_not_connect_to_services(tmp_path, machine, monkeypatch, capsys):
    path = tmp_path / "machines.json"
    path.write_text(json.dumps([machine.model_dump()]), encoding="utf-8")

    def no_connection(*args):
        pytest.fail("dry-run attempted to connect to Chroma")

    monkeypatch.setattr("app.agents.vision.knowledge.get_collection", no_connection)
    monkeypatch.setattr(settings, "azure_openai_api_key", None)
    main(["--file", str(path), "--dry-run"])
    assert "Validated 1 machine cards" in capsys.readouterr().out


def test_seed_duplicate_ids_are_rejected(tmp_path, machine):
    path = tmp_path / "machines.json"
    path.write_text(json.dumps([machine.model_dump(), machine.model_dump()]), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_machines(path)


def test_seed_rejects_incomplete_card(tmp_path):
    path = tmp_path / "machines.json"
    path.write_text('[{"machine_id": "incomplete"}]', encoding="utf-8")
    with pytest.raises(ValidationError):
        load_machines(path)


class ControlledCompletions:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        parsed, refusal = next(self.replies)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, refusal=refusal))])


def make_azure_llm(replies):
    completions = ControlledCompletions(replies)
    client = SimpleNamespace(beta=SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    return AzureVisionLLM(client, vision_deployment="vision-model", chat_deployment="text-model"), completions


def test_azure_routes_image_and_text_to_separate_deployments(machine):
    identification = MachineIdentification(machine_id=machine.machine_id, machine_name=machine.name)
    usage = MachineUsage.model_validate(machine.model_dump(include=set(MachineUsage.model_fields)))
    llm, completions = make_azure_llm([(identification, None), (usage, None)])

    async def run():
        knowledge = [MachineCatalogEntry(machine_id=machine.machine_id, name=machine.name, aliases=machine.aliases)]
        assert await llm.identify(b"\x89PNG image", knowledge) == identification
        assert await llm.describe(machine) == usage

    asyncio.run(run())
    vision_call, text_call = completions.calls
    assert vision_call["model"] == "vision-model"
    assert vision_call["response_format"] is MachineIdentification
    catalog_text = vision_call["messages"][1]["content"][0]["text"]
    assert json.loads(catalog_text.removeprefix("Supported catalog:\n")) == [
        {"machine_id": machine.machine_id, "name": machine.name, "aliases": machine.aliases}
    ]
    assert vision_call["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert text_call["model"] == "text-model"
    assert text_call["response_format"] is MachineUsage
    assert text_call["messages"][0]["content"].startswith(USAGE_SYSTEM_PROMPT)
    assert text_call["messages"][1]["role"] == "user"
    assert json.loads(text_call["messages"][1]["content"]) == machine.model_dump()


async def describe_with_sdk_response(machine, content, requests):
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "text-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
            },
        )

    async with AsyncAzureOpenAI(
        api_key="test-key",
        azure_endpoint="https://test.openai.azure.com/",
        api_version="2024-10-21",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ) as client:
        llm = AzureVisionLLM(client, vision_deployment="vision-model", chat_deployment="text-model")
        return await llm.describe(machine)


def test_sdk_sends_strict_schema_and_parses_valid_json(machine):
    payload = machine.model_dump(include=set(MachineUsage.model_fields))
    requests = []
    result = asyncio.run(describe_with_sdk_response(machine, json.dumps(payload), requests))

    assert result.model_dump() == payload
    assert len(requests) == 1
    request = requests[0]
    assert request["messages"][0]["content"].startswith(USAGE_SYSTEM_PROMPT)
    output_format = request["response_format"]
    assert output_format["type"] == "json_schema"
    assert output_format["json_schema"]["strict"] is True
    schema = output_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(MachineUsage.model_fields)


@pytest.mark.parametrize(
    "case",
    [
        "missing_field",
        "extra_field",
        "wrong_type",
        "blank_description",
        "blank_step",
        "empty_primary_muscles",
        "empty_setup_steps",
        "empty_exercise_steps",
        "invalid_json",
        "markdown",
    ],
)
def test_sdk_rejects_invalid_usage_output(machine, case):
    payload = machine.model_dump(include=set(MachineUsage.model_fields))
    match case:
        case "missing_field":
            del payload["description"]
        case "extra_field":
            payload["machine_name"] = "A name invented by the model"
        case "wrong_type":
            payload["setup_steps"] = "A string instead of an array"
        case "blank_description":
            payload["description"] = " "
        case "blank_step":
            payload["exercise_steps"] = [" "]
        case "empty_primary_muscles":
            payload["primary_muscles"] = []
        case "empty_setup_steps":
            payload["setup_steps"] = []
        case "empty_exercise_steps":
            payload["exercise_steps"] = []
    content = json.dumps(payload)
    if case == "invalid_json":
        content = "{not valid JSON}"
    elif case == "markdown":
        content = "```json\n" + content + "\n```"

    requests = []
    with pytest.raises(VisionModelResponseError, match="invalid structured response"):
        asyncio.run(describe_with_sdk_response(machine, content, requests))
    assert len(requests) == 1


def test_azure_refusal_is_reported_as_model_error(machine):
    llm, _ = make_azure_llm([(None, "Cannot answer")])
    with pytest.raises(VisionModelResponseError):
        asyncio.run(llm.describe(machine))


def test_openapi_marks_vision_endpoint_as_public():
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/agents/vision/analyze"]["post"]
    assert not operation.get("security")
    assert "multipart/form-data" in operation["requestBody"]["content"]
