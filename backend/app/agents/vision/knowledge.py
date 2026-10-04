from itertools import batched

from pydantic import ValidationError

from app.memory.chroma_client import get_collection
from app.schemas.vision import MachineCatalogEntry, MachineDocument


class MachineCardSchemaError(RuntimeError):
    pass


def load_stored_machine(document: str) -> MachineDocument:
    try:
        return MachineDocument.model_validate_json(document)
    except ValidationError as exc:
        raise MachineCardSchemaError(
            "Machine cards in Chroma use an outdated or invalid schema. "
            "Update all cards to canonical muscle region IDs and run python -m app.agents.vision.seed."
        ) from exc


class GymMachineKnowledge:

    def __init__(self) -> None:
        self.collection = get_collection("gym_machines")

    def seed(self, machines: list[MachineDocument]) -> int:
        identifiers = [machine.machine_id for machine in machines]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("machine_id values must be unique")
        for batch in batched(machines, 100):
            self.collection.upsert(
                ids=[machine.machine_id for machine in batch],
                documents=[machine.model_dump_json(indent=2) for machine in batch],
                metadatas=[{"machine_id": machine.machine_id, "category": machine.category} for machine in batch],
            )
        return len(machines)

    def get_catalog(self) -> list[MachineCatalogEntry]:
        result = self.collection.get(include=["documents"])
        machines = [load_stored_machine(doc) for doc in result["documents"] or []]
        return [
            MachineCatalogEntry(
                machine_id=machine.machine_id,
                name=machine.name,
                aliases=machine.aliases,
            )
            for machine in sorted(machines, key=lambda machine: machine.machine_id)
        ]

    def search(self, machine_name: str, machine_id: str) -> MachineDocument | None:
        if not self.count():
            return None
        result = self.collection.query(
            query_texts=[machine_name],
            n_results=1,
            where={"machine_id": machine_id},
            include=["documents"],
        )
        documents = result["documents"] or [[]]
        if not documents[0]:
            return None
        machine = load_stored_machine(documents[0][0])
        return machine if machine.machine_id == machine_id else None

    def count(self) -> int:
        return self.collection.count()
