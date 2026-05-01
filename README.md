# Santiago Nocturno — Creador de Personajes V5

Paquete formalizado en JSON. El JSON manda para Disciplinas; el Excel queda como referencia editorial.

## Archivos de producción

- `data/creator-data.json`: catálogos generales del creador en JSON formal.
- `data/aliases.json`: registro formal de aliases, migraciones editoriales y aliases rechazados; no es fuente canónica de reglas.
- `data/disciplinas_v5_catalogo.json`: catálogo mecánico autoritativo de Disciplinas, Rituales, Ceremonias y Alquimia.
- `derived/amalgamas_v5_index_derivado.json`: índice generado desde `records[].amalgamRequirement`; no se edita a mano.
- `schemas/*.schema.json`: esquemas JSON formales, incluido `aliases.schema.json`.
- `docs/creator-logic-spec.md`: especificación lógica actualizada sin nombres legacy.

## Fuente editorial

- `source/Disciplinas-error-corregido.xlsx`: respaldo editorial. No manda en producción.

## Herramientas

- `tools/generate_amalgama_index.py`: regenera el índice derivado.
- `tests/*.py`: pruebas unitarias con `unittest`.

## Dependencias

```bash
pip install -r requirements.txt
```

## Verificación rápida

```bash
python -m unittest discover -s tests
python tools/generate_amalgama_index.py
```

## Decisión sobre el script

No es necesario para ejecutar la app, pero sí es recomendable para mantener reproducibilidad. Por eso queda en `tools/`, no en `data/`.

## Conteos actuales

- Registros mecánicos: 402
- Poderes: 209
- Rituales: 105
- Ceremonias: 28
- Fórmulas de Alquimia de Sangre Débil: 60
- Amalgamas derivadas: 56
- Aliases activos de disciplinas: 2
- Aliases activos de ventajas (individuales): 16
- Aliases activos de dominio: 2
- Total aliases activos de ventajas/dominio: 18
- Aliases rechazados o con cambio de scope: 2
- Errata: 32
- Nombres visibles sin traducción pendiente: 0
