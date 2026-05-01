from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
TOOLS = ROOT / "tools"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

try:
    from character_validator import load_project_data, validate_character  # noqa: E402
    from validators.common import normalize_identifier  # noqa: E402
except ModuleNotFoundError as exc:  # pragma: no cover - mensaje operativo
    missing = exc.name or "dependencia"
    raise SystemExit(
        f"No se pudo iniciar la UI: falta {missing}.\n"
        "Ejecuta primero: pip install -r requirements.txt"
    ) from exc

DATA = load_project_data(ROOT)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discipline_power_payload() -> list[dict]:
    records = DATA["discipline_catalog"].get("records", [])
    powers = []
    for record in records:
        if record.get("kind") != "power":
            continue
        discipline = record.get("discipline", "")
        name = record.get("name", {})
        powers.append(
            {
                "id": record.get("id"),
                "discipline": discipline,
                "disciplineId": normalize_identifier(discipline),
                "level": record.get("level"),
                "name": name.get("es") or name.get("en") or record.get("id"),
                "amalgamRequirement": record.get("amalgamRequirement"),
            }
        )
    return sorted(powers, key=lambda item: (item["discipline"], item["level"], item["name"]))


def catalog_payload() -> dict:
    creator = DATA["creator_data"]
    return {
        "clans": creator.get("clanCatalog", []),
        "generations": creator.get("generationCatalog", []),
        "predators": creator.get("predatorTypes", []),
        "attributes": creator.get("attributes", []),
        "skills": creator.get("skills", []),
        "specialRequiredSkills": creator.get("specialRequiredSkills", []),
        "advantages": creator.get("advantagesCatalog", []),
        "domain": creator.get("domainCatalog", []),
        "powers": discipline_power_payload(),
        "creatorSteps": creator.get("creatorSteps", []),
    }


def validate_payload(state: dict, *, update_derived: bool = False) -> dict:
    return validate_character(
        state,
        DATA["creator_data"],
        discipline_catalog=DATA["discipline_catalog"],
        validation_rules=DATA["validation_rules"],
        character_schema=DATA["character_schema"],
        update_derived=update_derived,
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "KindredBuilderTestUI/1.0"

    def send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        content_type = "text/plain; charset=utf-8"
        if path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"

        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/catalogs":
            self.send_json(catalog_payload())
            return

        if path in {"/", "/index.html"}:
            self.send_file(STATIC / "index.html")
            return

        candidate = (STATIC / path.lstrip("/")).resolve()
        if STATIC in candidate.parents and candidate.exists() and candidate.is_file():
            self.send_file(candidate)
            return

        self.send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            self.send_json({"error": "JSON inválido", "details": str(exc)}, status=400)
            return

        if path == "/api/validate":
            self.send_json(validate_payload(payload, update_derived=False))
            return

        if path == "/api/finalize":
            self.send_json(validate_payload(payload, update_derived=True))
            return

        self.send_json({"error": "Not found"}, status=404)


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Interfaz disponible en http://{host}:{port}")
    print("Cierra con Ctrl+C.")
    server.serve_forever()


if __name__ == "__main__":
    main()
