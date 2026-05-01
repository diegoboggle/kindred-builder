import json
from pathlib import Path

try:
    from catalog_tools import catalog_record_checksum, generate_amalgam_index
except ModuleNotFoundError as exc:
    if exc.name != "catalog_tools":
        raise
    from .catalog_tools import catalog_record_checksum, generate_amalgam_index


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    catalog_path = ROOT / "data" / "disciplinas_v5_catalogo.json"
    index_path = ROOT / "derived" / "amalgamas_v5_index_derivado.json"

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    index = {
        "$schema": "../schemas/amalgam-index.schema.json",
        "schemaVersion": "amalgam-index-v2",
        "generated": True,
        "sourceCatalog": "data/disciplinas_v5_catalogo.json",
        "sourceCatalogChecksum": {"algorithm": "sha256", "value": catalog_record_checksum(catalog)},
        "entries": generate_amalgam_index(catalog),
    }
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f'Generated {index_path} with {len(index["entries"])} entries.')


if __name__ == "__main__":
    main()
