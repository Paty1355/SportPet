import argparse
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.schemas.vision import MachineDocument

DEFAULT_DATA_FILE = Path(__file__).resolve().parents[3] / "docs_RAG" / "vision" / "machines.json"


def load_machines(path: Path) -> list[MachineDocument]:
    machines = TypeAdapter(list[MachineDocument]).validate_json(path.read_text(encoding="utf-8-sig"))
    if not machines:
        raise ValueError("The file must contain at least one machine card")
    ids = [machine.machine_id for machine in machines]
    if len(ids) != len(set(ids)):
        raise ValueError("machine_id values must be unique")
    return machines


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate and import VisionAgent machine cards into Chroma.")
    parser.add_argument("--file", type=Path, default=DEFAULT_DATA_FILE, help="JSON array of machine cards")
    parser.add_argument("--dry-run", action="store_true", help="validate only; no Azure or Chroma connection")
    args = parser.parse_args(argv)
    try:
        machines = load_machines(args.file)
    except FileNotFoundError:
        parser.error(f"File not found: {args.file}. Create machines.json or explicitly select --file.")
    except (OSError, ValidationError, ValueError) as exc:
        parser.error(f"Invalid machine data: {exc}")
    if args.dry_run:
        print(f"Validated {len(machines)} machine cards from {args.file}; nothing was stored.")
        return

    from app.agents.vision.knowledge import GymMachineKnowledge
    from app.core.config import settings

    if not settings.azure_enabled:
        parser.error("Configure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY, or use --dry-run.")
    knowledge = GymMachineKnowledge()
    seeded = knowledge.seed(machines)
    print(f"Upserted {seeded} machine cards; {knowledge.collection.name}: {knowledge.count()} cards total.")


if __name__ == "__main__":
    main()
