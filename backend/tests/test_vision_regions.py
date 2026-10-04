import asyncio
import json
from io import BytesIO
from pathlib import Path
from typing import get_args

import pytest
from PIL import Image
from pydantic import ValidationError

from app.agents.vision.agent import VisionAgent, get_vision_agent
from app.agents.vision.knowledge import GymMachineKnowledge, MachineCardSchemaError
from app.agents.vision.seed import load_machines
from app.main import app
from app.schemas.vision import MachineDocument, MachineIdentification, MachineUsage, MuscleRegion, VisionResponse

DATA_PATH = Path(__file__).resolve().parents[1] / "docs_RAG" / "vision" / "machines.json"


@pytest.fixture
def card():
    return load_machines(DATA_PATH)[0]


class ProseLLM:
    def __init__(self, machine_id):
        self.machine_id = machine_id
        self.calls = []

    async def identify(self, image, catalog):
        self.calls.append("identify")
        return MachineIdentification(
            is_gym_equipment=True, confidence="high", machine_id=self.machine_id, machine_name="Ignored model name"
        )

    async def describe(self, machine_context):
        self.calls.append("describe")
        return MachineUsage(
            description="Push with your legs to train the front of your thighs.",
            setup_steps=["Sit down."],
            exercise_steps=["Push the platform."],
            tips=[],
        )


def image_file():
    output = BytesIO()
    Image.new("RGB", (16, 12), "green").save(output, format="PNG")
    return {"file": ("machine.png", output.getvalue(), "image/png")}


def test_response_regions_come_from_card_and_not_generated_prose(client, card):
    knowledge = GymMachineKnowledge()
    knowledge.seed([card])
    llm = ProseLLM(card.machine_id)
    app.dependency_overrides[get_vision_agent] = lambda: VisionAgent(llm, knowledge)

    response = client.post("/api/v1/agents/vision/analyze", files=image_file())
    assert response.status_code == 200
    body = response.json()
    assert body["primary_muscles"] == ["quads", "glutes"]
    assert body["secondary_muscles"] == ["hamstrings", "calves", "adductors"]
    assert body["description"] == "Push with your legs to train the front of your thighs."
    assert set(body) == set(VisionResponse.model_fields)
    assert llm.calls == ["identify", "describe"]


def test_support_equipment_can_return_empty_regions(client):
    bench = next(card for card in load_machines(DATA_PATH) if card.machine_id == "adjustable_bench")
    knowledge = GymMachineKnowledge()
    knowledge.seed([bench])
    app.dependency_overrides[get_vision_agent] = lambda: VisionAgent(ProseLLM(bench.machine_id), knowledge)

    response = client.post("/api/v1/agents/vision/analyze", files=image_file())
    assert response.status_code == 200
    assert response.json()["primary_muscles"] == []
    assert response.json()["secondary_muscles"] == []
    assert "muscle_notes" not in response.json()


@pytest.mark.parametrize("field", ["primary_muscles", "secondary_muscles"])
@pytest.mark.parametrize(
    "labels",
    [["Quadriceps"], ["front of your thighs"], ["Back"], ["hip-flexors"], ["quads", "quads"], [""], [42], "quads"],
)
def test_card_rejects_invalid_region_labels(card, field, labels):
    payload = card.model_dump()
    payload[field] = labels
    with pytest.raises(ValidationError):
        MachineDocument.model_validate(payload)
    response = card.model_dump(exclude={"name", "aliases", "muscle_notes"})
    response["machine_name"] = card.name
    response[field] = labels
    with pytest.raises(ValidationError):
        VisionResponse.model_validate(response)


def test_every_frontend_region_is_accepted(card):
    payload = card.model_dump()
    payload["primary_muscles"] = list(get_args(MuscleRegion.__value__))
    assert MachineDocument.model_validate(payload).primary_muscles == payload["primary_muscles"]


def test_catalog_is_normalized_and_unmapped_context_is_preserved():
    cards = {card.machine_id: card for card in load_machines(DATA_PATH)}
    for card in cards.values():
        assert set(card.primary_muscles + card.secondary_muscles) <= set(get_args(MuscleRegion.__value__))
    assert cards["pec_deck"].secondary_muscles == ["shoulders"]
    assert cards["lat_pulldown"].secondary_muscles == ["biceps", "rear-deltoids", "traps"]
    assert "Secondary: Rhomboids" in cards["lat_pulldown"].muscle_notes
    assert cards["hip_abductor_adductor"].primary_muscles == ["glutes", "adductors"]
    assert "Primary: Iliopsoas (Hip Flexors)" in cards["captains_chair"].muscle_notes
    assert "Secondary: Arms (if using moving handles)" in cards["elliptical_trainer"].muscle_notes
    assert "Secondary: Back" in cards["elliptical_trainer"].muscle_notes
    assert "lats" not in cards["elliptical_trainer"].secondary_muscles
    assert "Primary: Full Body (Varies by exercise)" in cards["dumbbells"].muscle_notes


def test_old_chroma_cards_return_503_until_reseeded(client, card):
    knowledge = GymMachineKnowledge()
    old_card = card.model_dump(exclude={"muscle_notes"})
    old_card["primary_muscles"] = ["Quadriceps", "Gluteus Maximus"]
    knowledge.collection.upsert(
        ids=[card.machine_id],
        documents=[json.dumps(old_card)],
        metadatas=[{"machine_id": card.machine_id, "category": card.category}],
    )
    llm = ProseLLM(card.machine_id)
    app.dependency_overrides[get_vision_agent] = lambda: VisionAgent(llm, knowledge)
    response = client.post("/api/v1/agents/vision/analyze", files=image_file())
    assert response.status_code == 503
    assert "python -m app.agents.vision.seed" in response.json()["detail"]
    assert llm.calls == []
    with pytest.raises(MachineCardSchemaError):
        knowledge.search(card.name, card.machine_id)

    knowledge.seed([card])
    assert knowledge.count() == 1
    result = asyncio.run(VisionAgent(llm, knowledge).run(b"image"))
    assert result.primary_muscles == card.primary_muscles
    assert llm.calls == ["identify", "describe"]
