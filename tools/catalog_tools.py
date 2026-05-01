import hashlib
import json


def catalog_record_checksum(catalog):
    payload = json.dumps(
        {"records": catalog["records"]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_amalgam_index(catalog):
    entries = []
    for record in catalog['records']:
        requirement = record.get('amalgamRequirement')
        if not requirement:
            continue
        entries.append({
            "requiredDiscipline": requirement["discipline"],
            "requiredLevel": int(requirement["level"]),
            "recordId": record["id"],
            "recordKind": record["kind"],
            "recordDiscipline": record["discipline"],
            "recordLevel": record["level"],
            "recordName": record["name"],
        })
    return sorted(entries, key=lambda item: (
        item["requiredDiscipline"],
        item["requiredLevel"],
        item["recordDiscipline"],
        item["recordLevel"],
        item["recordName"]["en"],
    ))
