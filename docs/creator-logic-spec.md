# Especificación lógica del Creador de Personajes

## 1. Catálogos base

Los datos generales están en `data/creator-data.json`. El catálogo mecánico de Disciplinas está separado en `data/disciplinas_v5_catalogo.json`, generado desde `Disciplinas-error-corregido.xlsx`. El registro de aliases está en `data/aliases.json` y sólo se usa para migración, resolución editorial y validación de nombres alternativos.

Esta especificación usa estos nombres lógicos:

- `CLANS`: lista de clanes disponibles.
- `GENERATIONS`: generaciones permitidas.
- `ATTRIBUTES`: atributos disponibles.
- `SKILLS`: habilidades disponibles.
- `SPECIAL_REQUIRED`: habilidades que requieren especialidad si tienen al menos 1 punto.
- `MALKAVIAN_PENALTY_CATEGORIES`: categorías válidas para el detalle Malkavian.
- `PUBLIC_DEATH_OPTIONS`: opciones públicas frente a la muerte documentada.
- `CLAN_INFO`: descripción, perdición, compulsión, disciplinas y detalles requeridos por clan.
- `CREATOR_STEPS`: orden lógico de pasos del creador.
- `PREDATOR_TYPES`: catálogo de tipos de depredador.
- `ADVANTAGES`: catálogo de méritos y defectos individuales.
- `DOMAIN_CATALOG`: catálogo de Dominio personal y rasgos territoriales.
- `DISABLED_COTERIE_CONTENT`: contenido de cotería conservado pero inhabilitado por inviabilidad con el estilo de la crónica.
- `DISCIPLINE_RECORDS`: registros externos de Disciplinas desde `data/disciplinas_v5_catalogo.json.records`.
- `ALIASES`: registro externo desde `data/aliases.json`; contiene aliases activos por scope y aliases rechazados. No reemplaza IDs canónicos.
- `AMALGAM_INDEX`: índice derivado desde `DISCIPLINE_RECORDS[].amalgamRequirement`; se regenera, no se edita a mano.
- `CONVICTION_OPTIONS` y `RELATION_OPTIONS`: sugerencias de texto para convicciones y relaciones.

`DISCIPLINE_RECORDS` es la única interfaz lógica para poderes, rituales, ceremonias y fórmulas. No se usan nombres legacy como fuente de datos.

## 2. Estructura del estado del personaje

El estado completo del creador debe modelarse así, de forma conceptual:

```text
CharacterCreatorState
  clan: string
  clanDetails:
    ventruePreyPreference: string
    malkavianAffliction: string
    malkavianPenaltyCategory: string
  generation: string
  sire:
    status: string
    origin: string
    state: string
    knowsName: boolean
    name: string
  basics:
    name: string
    concept: string
    ambition: string
  predator:
    type: string
    disciplineChoice: string
    specialtyChoice: string
    specialtyCustomValue: string
    pendingFlaw: string
    pendingFlawCustomValue: string
    awardDetails: map<string, string>
  attrSequence: list<string>
  attributes: map<attribute, integer>
  skillSequence: list<string>
  skills: map<skill, integer>
  specialties:
    - skill: string
      name: string
      source: optional string
  freeSpecialtySkill: string
  freeSpecialtyName: string
  disciplines:
    primary: string
    secondary: string
    powersByDiscipline: map<discipline, list<powerName>>
    bloodRitual: string
    oblivionCeremony: string
  advantages:
    merits: list<AdvantageSelection>
    flaws: list<AdvantageSelection>
    budget:
      totalMeritDots: integer
      spentMeritDots: integer
      contributedToDomainDots: integer
      availableMeritDots: integer
      totalFlawDots: optional integer
      spentFlawDots: optional integer
  domain:
    enabled: boolean
    pool:
      baseDots: integer
      contributedAdvantageDots: integer
      flawDots: integer
      grantedDots: integer
      spentDots: integer
    contributions:
      - id: string
        source: "characterAdvantages"
        sourceBudget: "advantages.meritDots"
        dots: integer
        reason: string
    traits:
      chasse: integer
      lien: integer
      portillon: integer
    backgrounds: list<DomainBackgroundSelection>
    merits: list<DomainSelection>
    flaws: list<DomainSelection>
  convictions:
    - conviction: string
      personName: string
      relation: string
    - conviction: string
      personName: string
      relation: string
    - conviction: string
      personName: string
      relation: string
  profile:
    portrait: string
    country: string
    city: string
    birth: string
    death: string
    publicDeath: string
    extraBio: string
  discordId: string
```

`AdvantageSelection` debe contener:

```text
AdvantageSelection
  traitId: string
  name: string
  dots: integer
  category: string
  type: "merit" | "flaw"
  description: optional string
  detail: optional string
  source: optional string
  automatic: optional boolean
```

## 3. Estado inicial

Al crear un personaje nuevo:

- `clan`, `generation`, campos de texto y selecciones empiezan vacíos.
- Todas las convicciones existen desde el inicio como tres filas vacías.
- Todos los atributos empiezan en 2.
- Todas las habilidades empiezan en 0.
- `attrSequence` empieza vacío.
- `skillSequence` empieza vacío.
- `disciplines.primary`, `disciplines.secondary`, `bloodRitual`, `oblivionCeremony` empiezan vacíos.
- `powersByDiscipline` empieza vacío.
- Méritos y defectos manuales empiezan vacíos.
- `advantages.budget.totalMeritDots` representa el presupuesto manual normal de Méritos.
- `advantages.budget.spentMeritDots` cuenta sólo Méritos individuales guardados en `advantages.merits`.
- `advantages.budget.contributedToDomainDots` empieza en 0 y debe coincidir con la suma de `domain.contributions`.
- `advantages.budget.availableMeritDots = totalMeritDots - spentMeritDots - contributedToDomainDots`.
- `domain.enabled` empieza en true.
- `domain.pool.baseDots` empieza en 1, como adaptación individual de la reserva de cotería.
- `domain.pool.contributedAdvantageDots`, `domain.pool.flawDots`, `domain.pool.grantedDots` y `domain.pool.spentDots` empiezan en 0.
- `domain.contributions` empieza vacío.
- `domain.traits.chasse`, `domain.traits.lien` y `domain.traits.portillon` empiezan en 0.
- `domain.backgrounds`, `domain.merits` y `domain.flaws` empiezan vacíos.

## 4. Orden de pasos

El creador tiene 12 pasos, en este orden:

1. `welcome` — Inicio
2. `clan` — Sangre
3. `sire` — Sire
4. `identity` — Identidad
5. `predator` — Depredador
6. `attributes` — Atributos
7. `skills` — Habilidades
8. `disciplines` — Disciplinas
9. `advantages` — Méritos y Defectos
10. `convictions` — Convicciones
11. `profile` — Perfil
12. `summary` — Resumen

El paso `welcome` y el paso `summary` siempre son válidos por sí mismos.

Para avanzar a un paso posterior, todos los pasos anteriores deben estar válidos. Se puede retroceder siempre.

Regla conceptual:

```text
canReachStep(currentStep, targetStep):
  if targetStep <= currentStep:
    return true
  for each stepIndex from 0 to targetStep - 1:
    if validateStep(stepIndex) is not valid:
      return false
  return true
```

## 5. Reglas de clan y generación

Validaciones:

- Debe elegirse un clan.
- Debe elegirse una generación.
- Si el clan es `Ventrue`, debe definirse `ventruePreyPreference`.
- Si el clan es `Malkavian`, debe definirse `malkavianAffliction`.
- Si el clan es `Malkavian`, debe elegirse `malkavianPenaltyCategory`.

Al cambiar de clan:

- Se conservan sólo los detalles relevantes para el nuevo clan.
- Si el nuevo clan no es Ventrue, se borra `ventruePreyPreference`.
- Si el nuevo clan no es Malkavian, se borran `malkavianAffliction` y `malkavianPenaltyCategory`.
- Se reinician las elecciones de depredador.
- Se reinician las disciplinas y poderes.
- Si el nuevo clan es Nosferatu, se eliminan méritos manuales de la categoría `Aspecto`.
- Si el nuevo clan es Ventrue, se elimina el defecto manual `Granjero`.

Conversión de generación:

```text
duodécima      -> 12
decimotercera -> 13
decimocuarta  -> 14
vacío/inválido -> null
```

## 6. Reglas del Sire

Campos obligatorios:

- `sire.status`
- `sire.origin`
- `sire.state`

Si `sire.knowsName` es verdadero, entonces `sire.name` debe tener texto.

## 7. Identidad básica

Campos obligatorios:

- `basics.name`
- `basics.concept`
- `basics.ambition`

## 8. Tipo de depredador

Un tipo de depredador define:

- descripción narrativa,
- reservas sugeridas,
- disciplinas posibles,
- restricciones de disciplina por clan,
- especialidades posibles,
- modificador de Humanidad,
- modificador de Potencia de Sangre,
- méritos automáticos,
- defectos automáticos,
- defectos pendientes a elegir,
- clanes prohibidos,
- máximo de Potencia de Sangre, si existe.

### 8.1 Disciplinas permitidas por depredador

Para obtener las disciplinas permitidas por depredador:

```text
getAllowedPredatorDisciplineChoices(predator, clan):
  result = []
  for each disciplineChoice in predator.disciplineChoices:
    restriction = predator.disciplineRestrictions[disciplineChoice]
    if restriction does not exist:
      include disciplineChoice
    else if restriction.clans does not exist:
      include disciplineChoice
    else if clan is empty:
      include disciplineChoice
    else if restriction.clans contains clan:
      include disciplineChoice
  return result
```

### 8.2 Validaciones de depredador

- Debe elegirse un tipo de depredador válido.
- Debe elegirse una disciplina de depredador permitida para el clan actual.
- Debe elegirse una especialidad de depredador.
- Si la especialidad contiene un placeholder que requiere detalle, debe completarse `specialtyCustomValue`.
- Si el tipo de depredador tiene defectos pendientes, debe elegirse uno.
- Si el defecto pendiente contiene un placeholder que requiere detalle, debe completarse `pendingFlawCustomValue`.
- Cada mérito/defecto automático de depredador que tenga un prompt de detalle debe tener texto en `predator.awardDetails`.

### 8.3 Opciones con detalle personalizado

Una elección requiere detalle personalizado si contiene alguno de estos textos:

- `animal concreto`
- `tradición concreta`
- `campo de entretenimiento concreto`
- `ambiente concreto`
- `subcultura distinta`
- `fuera de su subcultura`

Al resolver la elección personalizada, se sustituye el placeholder por el valor entregado.

Ejemplos:

```text
"Trato con Animales: animal concreto" + "perros callejeros"
-> "Trato con Animales: perros callejeros"

"Ocultismo: tradición concreta" + "Hermetismo"
-> "Ocultismo: Hermetismo"
```

### 8.4 Especialidades de depredador

Una especialidad se interpreta así:

```text
parseSpecialtyChoice(choice):
  if choice está vacío:
    return skill="", name=""

  if choice cumple "Habilidad: Especialidad":
    if Habilidad existe en SKILLS:
      return skill=Habilidad, name=Especialidad
    else:
      return skill="", name=Especialidad

  if choice cumple "Habilidad (Especialidad)":
    if Habilidad existe en SKILLS:
      return skill=Habilidad, name=Especialidad
    else:
      return skill="", name=choice

  otherwise:
    return skill="", name=choice
```

## 9. Atributos

### 9.1 Distribución de atributos

La regla estructurada vive en `data/creator-data.json.attributeCreationModel`. Hay 9 atributos. Todos empiezan en 2.

La distribución final obligatoria en creación inicial es:

```text
4/3/3/3/2/2/2/2/1
```

El creador usa una secuencia de selección `attrSequence` de exactamente 5 atributos modificados. La posición en la secuencia determina el valor final:

```text
posición 1 -> valor 4
posición 2 -> valor 1
posiciones 3, 4 y 5 -> valor 3
atributos no elegidos -> valor 2
```

Validación final:

- Exactamente 5 atributos modificados.
- Exactamente un atributo en 4.
- Exactamente tres atributos en 3.
- Exactamente cuatro atributos en 2.
- Exactamente un atributo en 1.

Regla de interacción sugerida:

```text
toggleAttribute(attribute):
  if attribute está en attrSequence:
    eliminarlo de attrSequence
  else if attrSequence tiene menos de 5 elementos:
    agregarlo al final
  reconstruir todos los atributos desde cero:
    todos comienzan en 2
    aplicar valores según posición en attrSequence
```

## 10. Habilidades

Hay 27 habilidades. Todas empiezan en 0.

El creador usa una secuencia de selección `skillSequence` de exactamente 10 habilidades. La posición en la secuencia determina el valor final:

```text
posición 1 -> valor 4
posiciones 2, 3 y 4 -> valor 3
posiciones 5, 6 y 7 -> valor 2
posiciones 8, 9 y 10 -> valor 1
habilidades no elegidas -> valor 0
```

Validación final:

- Exactamente 10 habilidades elegidas.
- Exactamente una habilidad en 4.
- Exactamente tres habilidades en 3.
- Exactamente tres habilidades en 2.
- Exactamente tres habilidades en 1.

### 10.1 Habilidades que requieren especialidad obligatoria

Si cualquiera de estas habilidades tiene al menos 1 punto, debe tener una especialidad asociada:

- `Academicismo`
- `Artesanía`
- `Ciencias`
- `Interpretación`

### 10.2 Especialidad libre

Si existe al menos una habilidad entrenada que no está en `SPECIAL_REQUIRED`, el personaje debe elegir una especialidad libre en una habilidad entrenada.

Condiciones:

- `freeSpecialtySkill` debe ser una habilidad con más de 0 puntos.
- `freeSpecialtyName` debe tener texto.

### 10.3 Restricciones relacionadas con defectos

- Si el personaje tiene el defecto `Analfabeto`, entonces `Academicismo` y `Ciencias` no pueden superar 1 punto.
- Si el personaje tiene el defecto `Transparente`, entonces `Subterfugio` debe ser 0.

Regla de interacción sugerida:

```text
toggleSkill(skill):
  if skill está en skillSequence:
    eliminarlo de skillSequence
  else if skillSequence tiene menos de 10 elementos:
    agregarlo al final
  reconstruir todas las habilidades desde cero:
    todas comienzan en 0
    aplicar valores según posición en skillSequence
  eliminar especialidades asociadas a habilidades que ahora tengan 0 puntos
  si freeSpecialtySkill ya no tiene puntos, limpiar freeSpecialtySkill y freeSpecialtyName
```

## 11. Disciplinas

Cada clan tiene 3 disciplinas de clan en `CLAN_INFO`.

El personaje elige:

- una disciplina primaria de clan,
- una disciplina secundaria de clan,
- una disciplina de depredador permitida.

El catálogo mecánico de Disciplinas se lee desde:

```text
data/disciplinas_v5_catalogo.json.records
```

Cada registro de Disciplina usa este modelo lógico, alineado con `schemas/discipline-catalog.schema.json`:

```text
DisciplineRecord
  id: string
  kind: "power" | "ritual" | "ceremony" | "thin_blood_formula"
  discipline: string
  level: integer
  name:
    en: string
    es: string
  text:
    en: map<string, string>
    es: map<string, string>
  source:
    raw: string
    items:
      - book: string
        bookEs: string
        page: string | null
        raw: string
  prerequisite:
    logic: "none" | "single" | "allOf" | "anyOf"
    conditions: list<PrerequisiteCondition>
    raw: string | null
  amalgamRequirement: null | { discipline: string, level: integer }
  errata: boolean
  errataFields: list<string>
  legacy: optional object
  translationStatus: optional "translated" | "unchanged_proper_term" | "missing"
```

`name.en` y `name.es` son los nombres visibles del registro. `text.en` y `text.es` contienen campos mecánicos localizados, como `effect`, `cost`, `duration`, `dicePool`, `opposingPool`, `ritualRoll`, `ingredients` o `notes`, según corresponda al tipo de registro. La app no debe esperar esos textos como propiedades planas del registro.

`source.raw` conserva la fuente editorial original para auditoría. La presentación debe preferir `source.items[]`, usando `book`, `bookEs` y `page` cuando estén disponibles.

`prerequisite.raw` conserva el texto original, pero la validación debe usar `prerequisite.logic` y `prerequisite.conditions`. Las condiciones estructuradas pueden apuntar a registros concretos mediante `candidateIds` cuando el prerrequisito se resolvió contra el catálogo.

Los registros con `kind = "power"` se usan para la selección normal de poderes. Los registros con `kind = "ritual"` se usan para rituales de Hechicería de Sangre. Los registros con `kind = "ceremony"` se usan para ceremonias de Olvido. Los registros con `kind = "thin_blood_formula"` no se usan en personajes vampiros estándar salvo que se implemente creación de Sangre Débil.

Las filas editoriales `Other Amalgams` del Excel no se importan como registros mecánicos. Cualquier vista de amalgamas debe generarse desde `amalgamRequirement`.

### 11.1 Validaciones de disciplinas principales

- Debe existir `disciplines.primary`.
- Debe existir `disciplines.secondary`.
- Ambas deben pertenecer a las disciplinas del clan.
- Primaria y secundaria deben ser distintas.

### 11.2 Cálculo de puntuaciones de disciplina

```text
ratings = empty map
if primary exists:
  ratings[primary] = 2
if secondary exists:
  ratings[secondary] = max(existing rating, 1)
if predator.disciplineChoice exists:
  ratings[predator.disciplineChoice] = min(5, existing rating + 1)
```

Consecuencias:

- Si la disciplina de depredador coincide con la primaria, sube de 2 a 3.
- Si coincide con la secundaria, sube de 1 a 2.
- Si es una disciplina distinta, queda en 1.

### 11.3 Poderes disponibles

Un poder estándar está disponible si:

- pertenece a la disciplina evaluada,
- `kind` es `power`,
- su nivel está entre 1 y la puntuación actual de la disciplina,
- cumple sus requisitos de amalgama,
- cumple sus prerrequisitos mecánicos detectables.

Los poderes disponibles se ordenan por nivel ascendente y luego por nombre.

### 11.4 Requisitos de amalgama

Un poder puede traer un requisito explícito:

```text
amalgamRequirement:
  discipline: string
  level: integer
```

El requisito se cumple si la puntuación calculada de la disciplina requerida es igual o superior al nivel requerido.

El índice de amalgamas no debe editarse manualmente. Si se necesita consultar qué poderes requieren una Disciplina, se genera así:

```text
buildAmalgamIndex(records):
  result = []
  for each record in records:
    if record.amalgamRequirement exists:
      add:
        requiredDiscipline = record.amalgamRequirement.discipline
        requiredLevel = record.amalgamRequirement.level
        powerId = record.id
        powerName = record.name
        powerDiscipline = record.discipline
        powerLevel = record.level
  return result
```



### 11.4.1 Prerrequisitos estructurados

Cada registro puede tener `prerequisite.logic` con `none`, `single`, `allOf` o `anyOf`. La validación no interpreta texto libre: usa las condiciones estructuradas. El texto original sólo se conserva en `prerequisite.raw` para auditoría.

### 11.4.2 Fuentes estructuradas

Cada registro conserva `source.raw`, pero la app debe mostrar preferentemente `source.items[]`, con `book`, `bookEs` y `page`.
### 11.5 Prerrequisitos no relacionados con amalgama

El campo `prerequisite` es un objeto estructurado. La validación automática sólo debe aplicar prerrequisitos mecánicos claros representados en `prerequisite.conditions`.

Regla mínima recomendada:

- `prerequisite.logic = "none"` significa “sin prerrequisito”.
- `prerequisite.raw` puede conservar valores editoriales como `None`, `No`, `N/A` o texto libre sólo para auditoría.
- Si una condición estructurada apunta a otro poder mediante `candidateIds`, ese poder debe estar seleccionado o disponible según la interpretación de mesa.
- Si `prerequisite.raw` contiene una condición de clan, línea de sangre, secta o regla narrativa no estructurada, mostrar advertencia en vez de bloquear automáticamente.

### 11.6 Selección de poderes

Para cada disciplina con puntuación `rating`, deben seleccionarse exactamente `rating` poderes válidos de `kind = "power"`.

Ejemplos:

```text
Disciplina con rating 1 -> 1 poder
Disciplina con rating 2 -> 2 poderes
Disciplina con rating 3 -> 3 poderes
```

Un poder seleccionado es inválido si:

- ya no aparece entre los poderes disponibles,
- está por encima de la puntuación actual,
- incumple un requisito de amalgama,
- incumple un prerrequisito mecánico claro.

### 11.7 Normalización de poderes

Cada vez que cambien clan, depredador, disciplina primaria, disciplina secundaria o disciplina de depredador, se debe normalizar la selección de poderes:

```text
normalizePowerSelections(state):
  ratings = getDisciplineRatings(state)
  next.primary = state.disciplines.primary
  next.secondary = state.disciplines.secondary
  next.powersByDiscipline = empty map

  if ratings["Hechicería de Sangre"] exists:
    next.bloodRitual = state.disciplines.bloodRitual
  else:
    next.bloodRitual = ""

  if ratings["Olvido"] exists:
    next.oblivionCeremony = state.disciplines.oblivionCeremony
  else:
    next.oblivionCeremony = ""

  for each discipline, rating in ratings:
    allowedNames = names of available kind="power" records for discipline/rating
    selected = previous selected powers for discipline
    keep only powers whose names are allowed
    remove duplicates preserving order
    keep at most rating powers
    next.powersByDiscipline[discipline] = selected

  return next
```

### 11.8 Ritual gratuito y ceremonia gratuita

- Si el personaje tiene Hechicería de Sangre con puntuación mayor que 0 y existen registros `kind = "ritual"`, `discipline = "Hechicería de Sangre"`, `level = 1`, debe elegir `bloodRitual`.
- Si el personaje tiene Olvido con puntuación mayor que 0 y existen registros `kind = "ceremony"`, `discipline = "Olvido"`, `level = 1`, debe elegir `oblivionCeremony`.

### 11.9 Errata

Los registros con `errata = true` son versiones actualizadas. La interfaz puede mostrar una marca discreta como “Actualizado”, pero no debe agregar la palabra `Errata` al nombre visible.

### 11.10 Compatibilidad con Voluntad Templada

Si el personaje tiene el mérito `Voluntad Templada`, no puede tener puntos en `Dominación` ni en `Presencia`.

## 12. Méritos y defectos

El creador distingue:

- méritos manuales,
- defectos manuales,
- méritos automáticos,
- defectos automáticos.

Los rasgos automáticos pueden venir del clan o del tipo de depredador y no cuentan para los puntos manuales.

### 12.1 Puntos manuales obligatorios

- Méritos manuales: exactamente 7 puntos.
- Defectos manuales: exactamente 2 puntos.

### 12.2 Rasgos automáticos de clan

Si el clan es `Nosferatu`, se agrega automáticamente:

```text
Defecto: Repulsivo ••
Fuente: Clan
Nota: Automático por Maldición Nosferatu. No cuenta para los 2 puntos manuales de defectos.
```

### 12.3 Rasgos automáticos de depredador

Los tipos de Depredador usan `automaticAwards` y `pendingFlawChoice`, no `grantedMerits`, `grantedFlaws` ni `pendingFlaws`.

`automaticAwards` admite tres formas:

```text
fixedTrait: aplica un Mérito o Defecto concreto.
choiceGroup: exige elegir una opción entre varias.
allocationGroup: exige distribuir totalDots entre opciones permitidas.
domainGrant: otorga puntos o rasgos al subsistema de Dominio personal.
```

Los rasgos automáticos nunca cuentan para los 7 puntos manuales de Méritos ni para los 2 puntos manuales de Defectos.

Los efectos con `scope: "domain"` no modifican `advantages.merits` ni `advantages.flaws`; modifican `character.domain`.

`pendingFlawChoice` se valida como elección obligatoria cuando no es null.

### 12.4 Identificación de rasgos automáticos

Los rasgos automáticos de depredador deben asociarse al catálogo mediante `traitId`.

Reglas:

- `traitId` es la referencia normativa.
- `name` se conserva como texto visible en español.
- No se deben crear rasgos individuales que no existan en `advantagesCatalog`.
- Los rasgos de Dominio deben existir en `domainCatalog`, no en `advantagesCatalog`.
- No se deben aceptar rasgos genéricos como `Mérito automático` o `Defecto automático`.
- Los textos defectuosos de extracción deben corregirse contra el rasgo oficial:
  - `Rebaño migrante` -> `Rebaño` (`merit_rebano`).
  - `Aspecto Bello` -> `Bello`.
  - `Contactos criminales` -> `Contactos`, con detalle narrativo `criminales`.
  - `Refugio: Espeluznante` -> `Espeluznante` (`flaw_refugio_espeluznante`).
  - `Refugio: Embrujado` -> `Embrujado` (`flaw_refugio_embrujado`).
  - `Dominio` no debe convertirse en ventaja individual; debe resolverse contra `domainCatalog`.

Si una opción individual no aparece en `advantagesCatalog`, debe eliminarse o sustituirse por el rasgo oficial equivalente. Si una opción territorial aparece como Dominio, debe resolverse contra `domainCatalog`. No debe quedar como texto libre.

Caso aplicado: `Recaudador de diezmos` ofrece una elección de 3 puntos entre `Estatus` (`merit_estatus`, `scope: "character"`) y `Dominio` (`domain_dominio`, `scope: "domain"`). En ambos casos conserva `Adversario` 2 (`flaw_mawla_adversario`) como defecto individual automático.

### 12.5 Dominio personal, contribuciones y contenido de cotería inhabilitado

La plataforma no implementa coterías multijugador ni grupos fijos. Por eso, las reglas de Dominio se adaptan como un subsistema individual del personaje:

```text
character.domain
```

Reglas:

- `Dominio` no existe en `advantagesCatalog`.
- `Dominio`, `Chasse`, `Lien` y `Portillon` existen en `domainCatalog`.
- Los puntos de Dominio se guardan en `character.domain.pool`.
- Los puntos de Dominio sólo pueden gastarse en rasgos de `domainCatalog`.
- Los puntos de Dominio no pueden comprar ventajas individuales guardadas en `character.advantages.merits`.
- Las ventajas individuales no pueden comprarse con puntos de Dominio.
- Los puntos del presupuesto normal de Méritos sí pueden transferirse al pool de Dominio, pero sólo mediante una contribución explícita en `character.domain.contributions`.
- Cada contribución debe indicar `source: "characterAdvantages"`, `sourceBudget: "advantages.meritDots"`, `dots` y `reason`.
- `domain.pool.contributedAdvantageDots` debe ser igual a la suma de `domain.contributions[*].dots` con fuente `characterAdvantages`.
- `advantages.budget.contributedToDomainDots` debe ser igual a esa misma suma.
- `advantages.budget.availableMeritDots = totalMeritDots - spentMeritDots - contributedToDomainDots`.
- Una contribución nunca puede contarse al mismo tiempo como Mérito individual comprado y como punto de Dominio.

Ejemplo de contribución válida:

```json
{
  "id": "domain_contribution_initial_01",
  "source": "characterAdvantages",
  "sourceBudget": "advantages.meritDots",
  "dots": 2,
  "reason": "Aporte voluntario a Dominio personal",
  "targetPool": "domain.pool.contributedAdvantageDots"
}
```

#### 12.5.1 Trasfondos adaptados al Dominio personal

Algunos trasfondos que oficialmente pueden comprarse en común con puntos de cotería se adaptan al modo individual como rasgos de `domainCatalog` con `type: "domainBackground"`. Esto permite distinguir entre:

```text
Mérito individual: character.advantages.merits[]
Trasfondo de Dominio personal: character.domain.backgrounds[]
```

Ejemplo:

```json
{
  "domainTraitId": "domain_background_rebano",
  "sourceTraitId": "merit_rebano",
  "dots": 2,
  "purchaseScope": "domain"
}
```

La entrada anterior representa Rebaño comprado con puntos de Dominio personal. No debe añadirse también a `advantages.merits`, porque eso duplicaría el gasto.

Trasfondos adaptados actualmente:

- `domain_background_aliados` desde `merit_aliados`.
- `domain_background_contactos` desde `merit_contactos`.
- `domain_background_fama` desde `merit_fama`.
- `domain_background_influencia` desde `merit_influencia`.
- `domain_background_refugio` desde `merit_refugio`.
- `domain_background_rebano` desde `merit_rebano`.
- `domain_background_mawla` desde `merit_mawla`.
- `domain_background_recursos` desde `merit_recursos`.
- `domain_background_criados` desde `merit_criados`.
- `domain_background_mascara` desde `merit_mascara`.
- `domain_background_estatus` desde `merit_estatus`.

Los defectos de trasfondo compatibles con Dominio personal se guardan como `domainBackgroundFlaw`. Al tomarse en este ámbito, aumentan `domain.pool.flawDots` y se guardan en `character.domain.flaws`, no en `character.advantages.flaws`.

#### 12.5.2 Fórmulas de validación de presupuesto

```text
domainPoolAvailable =
  domain.pool.baseDots
  + domain.pool.contributedAdvantageDots
  + domain.pool.flawDots
  + domain.pool.grantedDots

domainPoolSpent =
  domain.traits.chasse
  + domain.traits.lien
  + domain.traits.portillon
  + sum(domain.backgrounds[].dots)
  + sum(domain.merits[].dots)

advantageMeritDotsAvailable =
  advantages.budget.totalMeritDots
  - advantages.budget.spentMeritDots
  - advantages.budget.contributedToDomainDots
```

Validaciones obligatorias:

- `domainPoolSpent <= domainPoolAvailable`.
- `domain.pool.spentDots == domainPoolSpent`.
- `domain.pool.contributedAdvantageDots == sum(domain.contributions[].dots)`.
- `advantages.budget.contributedToDomainDots == sum(domain.contributions[].dots)`.
- `advantages.budget.availableMeritDots == advantageMeritDotsAvailable`.
- `advantageMeritDotsAvailable >= 0`.

El helper `tools/character_budget_tools.py` implementa estas comprobaciones para las pruebas unitarias y para reutilización en la app.

#### 12.5.3 Contenido de cotería inhabilitado

El contenido de cotería incompatible se conserva en `disabledCoterieContent` con `status: "disabled"` y motivo `Inviable con el estilo de la crónica`.

Contenido de cotería inhabilitado por estilo de crónica:

- Tipos de cotería.
- Reserva colaborativa de cotería.
- Ventajas y defectos de cotería que presuponen grupo conocido o recursos compartidos.
- Méritos de clan de cotería que presuponen compañeros de cotería.
- Reglas de pertenencia a múltiples coterías o cambio de cotería.

### 12.6 Prerrequisitos e incompatibilidades estructuradas

Los rasgos del catálogo pueden declarar relaciones de reglas:

```json
{
  "requires": [
    {
      "type": "trait",
      "traitId": "merit_refugio",
      "minDots": 1
    }
  ],
  "incompatibleWith": [
    "flaw_refugio_sin_refugio"
  ]
}
```

Reglas mínimas actuales:

- `Sin Refugio` es incompatible con `Refugio`.
- Todo rasgo de la categoría `Refugio`, salvo `Refugio` y `Sin Refugio`, requiere `Refugio` al menos a 1 punto.
- `Celda` y `Laboratorio` requieren `Refugio` al menos a 2 puntos.
- `Blindado`, `Alijo de Contrabandistas`, `Matrículas de Repuesto`, `Sobre Raíles` y `Temperamental` requieren `Móvil`.
- `Influencer` requiere `Fama` al menos a 2 puntos.
- `Fama Duradera` requiere `Fama` al menos a 3 puntos.

### 12.7 Bloqueos de ventajas

Un rasgo no puede elegirse si se cumple una de estas condiciones:

- Clan `Nosferatu` + mérito de categoría `Aspecto`: bloqueado.
- Clan `Ventrue` + defecto `Granjero`: bloqueado.
- Mérito `Voluntad Templada` + el personaje tiene puntos en `Dominación` o `Presencia`: bloqueado.
- Defecto `Analfabeto` + `Academicismo` > 1 o `Ciencias` > 1: bloqueado.
- Defecto `Transparente` + `Subterfugio` > 0: bloqueado.
- El mismo rasgo ya existe con igual nombre, tipo y categoría: bloqueado.
- Existe otro rasgo del mismo grupo exclusivo: bloqueado.

### 12.8 Grupos exclusivos de rasgos

Estos grupos impiden tomar rasgos incompatibles entre sí:

```text
Grupo aspecto.belleza:
  Bello
  Despampanante
  Feo
  Repulsivo
  o cualquier nombre de categoría Aspecto que contenga esas palabras

Grupo recursos.economia:
  Recursos
  Indigente
  o cualquier nombre de categoría Recursos que contenga esas palabras

Grupo linguistica.alfabetizacion:
  Lingüística
  Analfabeto

Grupo psicologicos.penitencia:
  Penitencia
  Gusano Servil
```

### 12.9 Validaciones de ventajas

Para cada mérito o defecto manual:

- Debe existir en el catálogo actual.
- Su puntuación debe estar en `dotOptions`.
- Si el catálogo marca `requiresDetail`, debe existir `detail`.
- No debe violar las reglas de bloqueo.

Para todos los rasgos manuales y automáticos combinados:

- No puede haber duplicados por `type + category + normalizedName`.
- No puede haber más de un rasgo dentro del mismo grupo exclusivo.

## 13. Convicciones y Piedras de Toque

El personaje tiene exactamente 3 convicciones.

Cada una debe tener:

- `conviction`
- `personName`
- `relation`

Cada fila incompleta produce un error específico indicando el número de convicción.

## 14. Perfil y biografía

Campos obligatorios:

- `profile.portrait`
- `profile.country`
- `profile.city`
- `profile.birth`
- `profile.death`
- `profile.publicDeath`
- `profile.extraBio` con al menos 500 caracteres reales
- `discordId`

Validaciones de fecha:

- `birth` no puede ser posterior a `death`.
- Si `birth` y `death` son iguales, se genera una advertencia, no un error.

Validación de Discord ID:

```text
Debe coincidir con el patrón: sólo dígitos, entre 17 y 20 caracteres.
```

Expresión equivalente:

```text
^[0-9]{17,20}$
```

## 15. Estadísticas derivadas

### 15.1 Humanidad

```text
humanity = 7 + predator.humanityMod
humanity se limita al rango 0..10
```

Si no hay depredador, usar modificador 0.

### 15.2 Potencia de Sangre

Regla de mesa:

```text
baseBloodPotency = 1
rawBloodPotency = baseBloodPotency + predator.bloodPotencyMod
bloodPotency = max(0, rawBloodPotency)
```

Si el depredador define `maxBloodPotency`, entonces:

```text
bloodPotency = min(bloodPotency, predator.maxBloodPotency)
```

### 15.3 Salud

```text
health = Resistencia + 3
```

### 15.4 Fuerza de Voluntad

```text
willpower = Compostura + Resolución
```

### 15.5 Número de generación

Ver sección de generación.

## 16. Especialidades finales

Las especialidades finales incluyen:

1. Especialidades manuales en habilidades que todavía tengan más de 0 puntos y tengan nombre.
2. Especialidad de depredador resuelta, si logra identificarse una habilidad válida.

Luego se eliminan duplicados por combinación:

```text
skill + ":" + lowercase(name)
```

La especialidad de depredador debe incluir `source = "Depredador"`.

## 17. Biografía automática

Si existen `basics.name`, `profile.city`, `profile.country`, `profile.birth` y `profile.death`, generar:

```text
[NOMBRE] fue un vástago que habitó en [CIUDAD], [PAÍS]. En vida mortal nació el [NACIMIENTO]; su muerte documentada figura el [MUERTE]. [FRASE SEGÚN publicDeath]
```

Frases según `publicDeath`:

```text
Saben que está muerto -> "El mundo mortal sabe que murió."
Finge seguir vivo     -> "Ante el mundo mortal, aún finge seguir vivo."
No está claro / otro  -> "Su estado ante el mundo mortal permanece ambiguo."
```

Si falta algún dato fundamental:

```text
La información biográfica fundamental aún está incompleta.
```

## 18. Validación total

La validación total ejecuta los validadores por paso en este orden:

```text
0 welcome     -> siempre válido
1 clan        -> validateClan
2 sire        -> validateSire
3 identity    -> validateBasics
4 predator    -> validatePredator
5 attributes  -> validateAttributes
6 skills      -> validateSkills
7 disciplines -> validateDisciplines
8 advantages  -> validateAdvantages
9 convictions -> validateConvictions
10 profile    -> validateProfile
11 summary    -> siempre válido
```

Cada validador devuelve:

```text
ValidationResult
  valid: boolean
  errors: list<string>
  warnings: list<string>
```

## 19. Exportación lógica del personaje

Al exportar, primero debe validarse todo el personaje. Si existe algún error, no debe exportarse.

El payload lógico debe contener:

```text
version: "creator-v5"
creatorState: estado completo
basics
clan
clanDetails
generation:
  label
  number
sire
predator:
  todo predator
  specialtyResolved
  pendingFlawResolved
attributes
skills
specialties finales
disciplines:
  catalogSource: "data/disciplinas_v5_catalogo.json"
  ratings
  powers:
    - id
      discipline
      name
      level
      rating
      errata
  bloodRitual:
    id
    name
    level
    errata
  oblivionCeremony:
    id
    name
    level
    errata
advantages:
  manual
  automatic
convictions
profile
discordId
derived:
  humanity
  bloodPotency
  health
  willpower
  generationNumber
autoBiography
validation
```

No exportar las filas `Other Amalgams` como poderes. Si se necesita un índice de amalgamas, puede exportarse como dato derivado opcional, nunca como fuente de verdad.

## 20. Nombre seguro de archivo

Para generar nombres de archivo:

```text
sanitizeFilename(value):
  if value está vacío: usar "personaje"
  remover acentos/diacríticos
  reemplazar cualquier carácter que no sea letra, número, guion o guion bajo por "_"
  eliminar guiones bajos al inicio y final
  si queda vacío: usar "personaje"
```

## 21. Restauración, migración y almacenamiento

Esta parte es opcional si el futuro proyecto no usa almacenamiento local, pero la lógica original funcionaba así.

Versión actual:

```text
creator-v5
```

Clave principal de borrador:

```text
santiago-nocturno:creator:v5:draft
```

Claves legacy aceptadas:

```text
santiago-nocturno:creator:v4:draft
santiago-nocturno:creator:v3.3:draft
santiago-nocturno:creator:v3.2:draft
santiago-nocturno:creator:v3.1:draft
santiago-nocturno:creator:v3:draft
```

Formato de borrador:

```text
StoredCreatorDraft
  version: string
  savedAt: ISO date string
  state: CharacterCreatorState
```

Reglas de migración:

- Si un valor no es objeto, no se puede restaurar.
- Si existe `creatorState`, restaurar desde ahí.
- Si existe `state`, restaurar desde ahí.
- Si no, intentar restaurar desde el objeto raíz.
- Los strings inválidos se convierten en string vacío.
- Las listas de atributos y habilidades se limpian, eliminan duplicados, filtran valores no permitidos y se recortan al máximo permitido.
- Atributos se limitan al rango 1..4.
- Habilidades se limitan al rango 0..4.
- Méritos y defectos restaurados deben tener nombre, categoría y puntos > 0.
- Convicciones siempre se restauran como exactamente 3 filas.
- Al final de la migración se normalizan las disciplinas.

## 22. Texto de reglas de poderes

Los textos mecánicos de Disciplinas se leen desde `data/disciplinas_v5_catalogo.json`.

Reglas de presentación:

- No mostrar `Errata` como parte del nombre del poder.
- Si `errata = true`, mostrar una marca discreta como “Actualizado” si la interfaz lo necesita.
- No depender de la traducción textual para validar reglas.
- La validación debe usar campos estructurados: `kind`, `discipline`, `level`, `amalgamRequirement`, `prerequisite`, `id` y `name`.
- Si se traduce el catálogo al español más adelante, mantener los IDs estables.

## 23. Registro formal de aliases

`data/aliases.json` centraliza nombres alternativos, nombres erróneos de extracción, aliases editoriales y cambios de scope. Su función es resolver entradas heredadas sin convertir el nombre visible en fuente de verdad.

Reglas:

```text
Si existe un ID canónico, la validación usa el ID.
Si existe `raw`, se conserva para trazabilidad editorial.
Si un alias está en `disciplineRecordAliases`, debe apuntar a `data/disciplinas_v5_catalogo.json.records`.
Si un alias está en `advantageTraitAliases`, debe apuntar a `data/creator-data.json.advantagesCatalog`.
Si un alias está en `domainTraitAliases`, debe apuntar a `data/creator-data.json.domainCatalog`.
Si una entrada está en `rejectedAliases`, no debe resolverse automáticamente como rasgo válido.
```

Ejemplos activos:

```text
Oblivion's Sight -> olvido_1_oblivion_sight
Where the Shroud Thins -> olvido_2_where_the_veil_thins
Refugio: Espeluznante -> flaw_refugio_espeluznante
Refugio: Embrujado -> flaw_refugio_embrujado
Dominio -> domain_dominio
```

Ejemplos rechazados o con cambio de scope:

```text
Rebaño migrante no es un rasgo oficial independiente.
Dominio no es una ventaja individual; pertenece al scope domain.
```

## 24. Reglas que requieren revisión manual si cambias el sistema

Estas reglas están acopladas a decisiones de mesa o a interpretación del proyecto original:

- Las generaciones 12, 13 y 14 empiezan todas con Potencia de Sangre base 1.
- Los Nosferatu reciben `Repulsivo ••` automático y no pueden comprar méritos de Aspecto.
- Los Ventrue no pueden escoger `Granjero` como defecto ni como tipo de depredador asociado.
- La lista de clanes no incluye Hécata, pero algunos tipos de depredador tienen restricciones históricas que mencionan Hécata; en esta implementación, eso deja esas opciones inaccesibles para los clanes disponibles.
- La exportación HTML original era visual; para independencia total, conserva sólo el payload lógico.
- Las filas `Other Amalgams` del Excel no forman parte del catálogo mecánico; el índice de amalgamas se deriva desde `amalgamRequirement`.


### Corrección del paso 9: Exclusión de Presa

`Exclusión de Presa` es un defecto de Alimentación de 1 punto. Las variantes usadas por depredadores no crean rasgos nuevos ni alteran el valor del defecto. En cambio, usan el mismo `traitId` canónico y guardan el grupo excluido en `detailDefault`.

Ejemplo:

```json
{
  "kind": "fixedTrait",
  "type": "flaw",
  "scope": "character",
  "name": "Exclusión de Presa",
  "dots": 1,
  "traitId": "flaw_alimentacion_exclusion_de_presa",
  "detailDefault": "mortales"
}
```

Reglas:

- `traitId` debe ser `flaw_alimentacion_exclusion_de_presa`.
- `dots` debe ser `1`, porque el catálogo oficial sólo permite `dotOptions: [1]`.
- El detalle específico, como `mortales`, `locales`, `sin consentimiento` o `mortales sanos`, debe ir en `detailDefault`.
- No se deben crear nombres compuestos como rasgos distintos, por ejemplo `Exclusión de Presa: mortales`.



### Corrección del paso 12: validación exhaustiva de rasgos automáticos de depredador

Los rasgos entregados por `PREDATOR_TYPES[].automaticAwards` y `pendingFlawChoice` deben ser resolubles sin depender de nombres libres.

Reglas aplicadas:

- Todo rasgo individual debe usar `scope: "character"` explícito o implícito y un `traitId` existente en `advantagesCatalog`.
- Todo rasgo de Dominio personal debe usar `scope: "domain"` y un `traitId` existente en `domainCatalog`.
- El `name` visible de un rasgo referenciado por `traitId` debe coincidir con el nombre canónico del catálogo. Las variantes específicas no van en `name`; van en `detailDefault`.
- Si el rasgo del catálogo tiene `requiresDetail: true`, la concesión de depredador debe declarar `detailDefault` o `detailRequired: true`.
- Los grupos `choiceGroup` y `allocationGroup` deben tener `options` no vacías.
- Las opciones de grupo deben resolverse mediante `traitId` o mediante `selectionFilter` estructurado.
- No se permiten opciones sueltas por categoría, por ejemplo `{ "category": "Míticos" }`.
- Las opciones por categoría deben declararse así:

```json
{
  "name": "Defecto Mítico",
  "category": "Míticos",
  "selectionFilter": {
    "scope": "character",
    "type": "flaw",
    "category": "Míticos"
  },
  "detailRequired": true
}
```

Normalizaciones aplicadas:

- `Secreto Oscuro: Diabolista` se modela como `name: "Secreto Oscuro"` y `detailDefault: "Diabolista"`.
- `Secreto Oscuro: cleaver` se modela como `name: "Secreto Oscuro"` y `detailDefault: "cleaver"`.
- `Despreciado: fuera de su subcultura` se modela como `name: "Despreciado"` y `detailDefault: "fuera de su subcultura"`.
- Las notas mecánicas de `Enemigo` y `Contactos` otorgados por depredador se copian a `detailDefault`, cuando corresponden al detalle inicial del rasgo.


### Corrección del paso 13: validación formal de prerrequisitos de disciplinas

Los prerrequisitos de `disciplinas_v5_catalogo.json` deben estar completamente estructurados. No se permite que el creador dependa de texto libre para determinar si un poder, ceremonia, ritual o fórmula está disponible.

Reglas aplicadas:

- `prerequisite.logic` sólo puede ser `none`, `single`, `allOf` o `anyOf`.
- Si `logic` es `none`, `conditions` debe estar vacío.
- Si `logic` es `single`, debe existir exactamente una condición.
- Si `logic` es `allOf` o `anyOf`, deben existir al menos dos condiciones.
- Las condiciones hoja sólo pueden ser de tipo `record` o `clan`.
- No puede quedar ninguna condición de tipo `unresolved`.
- Toda condición `record` debe declarar `raw`, `name`, `nameEs` y `candidateIds`.
- Todo `candidateId` debe apuntar a un registro existente del catálogo.
- Ningún registro puede referenciarse a sí mismo como prerrequisito.
- Los prerrequisitos por registro deben resolver a poderes (`kind: "power"`), no a rituales, ceremonias ni fórmulas.
- Las diferencias entre `raw` y el nombre canónico deben estar registradas en `data/aliases.json`.
- Los requisitos de amalgama deben tener disciplina conocida, nivel entre 1 y 5, y texto `raw` de origen.
- `derived/amalgamas_v5_index_derivado.json` no debe contener entradas faltantes ni obsoletas respecto del catálogo de disciplinas.

Casos de alias obligatorios:

```text
Oblivion's Sight -> olvido_1_oblivion_sight
Where the Shroud Thins -> olvido_2_where_the_veil_thins
```

Estas reglas quedan cubiertas por `tests/test_discipline_prerequisites.py`.


### Corrección del paso 14: reglas bloqueantes de validación

Las restricciones de clan, defecto, ventaja, disciplina, habilidad y Dominio personal se definen en un archivo independiente:

```text
data/validation-rules.json
schemas/validation-rules.schema.json
tests/test_validation_rules.py
```

`creator-data.json` no debe contener un bloque `validationRules`. Su responsabilidad es mantener catálogos canónicos; `validation-rules.json` mantiene combinaciones permitidas o prohibidas.

Cada regla declara:

```json
{
  "id": "rule_ventrue_cannot_take_farmer",
  "scope": "character",
  "origin": "official",
  "severity": "error",
  "description": "Los Ventrue no pueden adquirir el Defecto Granjero.",
  "when": {
    "clanId": "clan_ventrue"
  },
  "effect": {
    "type": "forbidTrait",
    "catalog": "advantages",
    "traitId": "flaw_alimentacion_granjero"
  }
}
```

Campos normativos:

- `origin: "official"` indica una restricción explícita en los textos o en la descripción oficial del rasgo.
- `origin: "logical"` indica una restricción derivada de la lógica del modelo o del estilo de crónica individual.
- `severity` siempre debe ser `"error"`.
- No existen advertencias flexibles para estas reglas. Toda infracción bloquea la creación o actualización del personaje.
- Las reglas con `scope: "domain"` aplican al subsistema de Dominio personal.
- Las reglas de presupuesto distinguen entre contribuciones reversibles desde Ventajas y puntos nativos de Dominio.

#### Presupuesto entre Ventajas y Dominio personal

Durante la creación, un jugador puede mover puntos de su presupuesto de Ventajas individuales al pool de Dominio personal para planificar la distribución. Este movimiento es reversible mientras el personaje no esté finalizado: si se elimina o reduce la contribución, esos puntos vuelven a estar disponibles para Ventajas individuales. La reversibilidad sólo aplica a puntos cuyo origen sea `characterAdvantages` y `sourceBudget: "advantages.meritDots"`.

Los puntos propios de Dominio personal no son reversibles hacia Ventajas. Esto incluye `domain.pool.baseDots`, `domain.pool.flawDots` y `domain.pool.grantedDots`. Esos puntos sólo pueden permanecer en Dominio personal y gastarse en `Chasse`, `Lien`, `Portillon`, trasfondos de Dominio o rasgos de Dominio compatibles.

La validación presupuestaria usa estas igualdades:

```text
domain.pool.contributedAdvantageDots == sum(domain.contributions[source=characterAdvantages].dots)
advantages.budget.contributedToDomainDots == domain.pool.contributedAdvantageDots
advantages.budget.availableMeritDots == totalMeritDots - spentMeritDots - contributedToDomainDots
domain.pool.spentDots == Chasse + Lien + Portillon + domain.backgrounds + domain.merits
```

Esta regla permite planificación flexible sin duplicar puntos: un mismo punto no puede estar simultáneamente gastado como Ventaja individual y como Dominio personal.

Reglas oficiales incorporadas:

- Ventrue no puede adquirir `Granjero`.
- `Analfabeto` limita `Academicismo` y `Ciencias` a máximo 1.
- `Transparente` impide adquirir puntos en `Subterfugio`.
- `Arcaico` fija `Tecnología` en 0.
- `Voluntad Templada` exige no tener `Dominación` ni `Presencia`.
- `Vínculos de Lealtad` requiere `Dominación`.
- `Gusano Servil` es incompatible con `Penitencia`.
- `Sangre Favorecida` es incompatible con `Sangre Embarrada`.
- `Liquidador` es incompatible con `Tío Colmillos`.
- `Influencer` requiere `Fama` 2 o superior.
- `Fama Duradera` requiere `Fama` 3 o superior.
- `Borrado` y `Curtidor` requieren `Máscara` 2.
- `Amo Secreto` requiere `Mawla`.
- `Depredador Manifiesto` bloquea `Rebaño`.
- `Celda` y `Laboratorio` requieren `Refugio` 2.
- Los rasgos de Refugio Móvil requieren `Refugio Móvil`.

Reglas lógicas incorporadas:

- Nosferatu no puede adquirir Méritos positivos de `Aspecto`.
- `Sin Refugio` bloquea `Refugio` y cualquier rasgo dependiente de `Refugio`.
- Todo rasgo de `Refugio`, salvo `Refugio` y `Sin Refugio`, requiere `Refugio` 1.
- Los trasfondos de Dominio personal sólo pueden comprarse con el pool de Dominio personal.
- El pool de Dominio personal puede incluir puntos base, puntos concedidos, defectos de Dominio y puntos actualmente aportados desde Ventajas individuales.
- Los puntos de Ventajas individuales pueden reasignarse hacia o desde Dominio personal durante la creación. Mientras estén asignados a Dominio, se descuentan del presupuesto normal de Ventajas.
- Los puntos nativos de Dominio personal (`baseDots`, `flawDots`, `grantedDots`) no pueden moverse al presupuesto de Ventajas ni comprar Ventajas individuales.
- `Sin Refugio` de Dominio personal bloquea `Refugio` de Dominio personal y sus defectos asociados.
- Los defectos de Refugio adaptados al Dominio personal requieren `Refugio` de Dominio personal.
- `Depredador Manifiesto` también bloquea `Rebaño` comprado como trasfondo de Dominio personal.
- `Refugio` de Dominio personal y `Sin Refugio` de Dominio personal son incompatibles.

Estas reglas quedan cubiertas por `tests/test_validation_rules.py`.


### Corrección del paso 16: distribución de habilidades

La creación inicial de habilidades queda formalizada en `data/creator-data.json` mediante `skillCreationModel`.

Distribución de habilidades obligatoria:

```text
4/3/3/3/2/2/2/1/1/1
```

Todas las demás habilidades quedan en 0. El personaje debe tener exactamente 27 habilidades en el mapa final, sin habilidades desconocidas ni campos extra.

El creador usa `skillSequence` como secuencia de 10 habilidades únicas. La posición en la secuencia determina el valor final:

```text
posición 1 -> 4
posiciones 2, 3 y 4 -> 3
posiciones 5, 6 y 7 -> 2
posiciones 8, 9 y 10 -> 1
habilidades no elegidas -> 0
```

`character-state.schema.json` define ahora de forma estricta:

```text
skillSequence
skills
specialties
freeSpecialtySkill
freeSpecialtyName
```

Reglas de validación:

- `skillSequence` debe contener exactamente 10 habilidades únicas y válidas.
- `skills` debe contener exactamente las 27 habilidades oficiales.
- Los valores iniciales de habilidades deben estar entre 0 y 4.
- La distribución final debe coincidir exactamente con `4/3/3/3/2/2/2/1/1/1`.
- `skills` debe coincidir con lo derivado desde `skillSequence`.
- `Academicismo`, `Artesanía`, `Ciencias` e `Interpretación` requieren especialidad si tienen al menos 1 punto.
- Todo personaje debe tener exactamente una especialidad gratuita.
- La especialidad gratuita debe apuntar a una habilidad entrenada, tener nombre no vacío y existir dentro de `specialties[]` con `source: "free"`.
- Toda especialidad debe declarar origen mediante `source`.
- Valores permitidos de `source`: `free`, `predator`, `advantage`, `manual`, `other`.
- Las especialidades por depredador sólo se aplican si la habilidad correspondiente tiene al menos 1 punto.
- Las especialidades no pueden apuntar a habilidades con 0 puntos.
- La cantidad de especialidades de una habilidad no puede superar la cantidad de puntos de esa habilidad.
- Las especialidades duplicadas dentro de la misma habilidad son inválidas usando coincidencia exacta normalizada: mayúsculas, minúsculas, acentos y espacios no crean nombres distintos.
- No se aplica bloqueo semántico de especialidades. Por ejemplo, `Seducir` y `Seducción` no se consideran duplicadas automáticamente.
- Las reglas bloqueantes de `validation-rules.json` pueden imponer máximos, por ejemplo `Analfabeto`, `Transparente` y `Arcaico`.

Ejemplo de especialidades con origen explícito:

```json
[
  {
    "skill": "Interpretación",
    "name": "Cantar",
    "source": "free"
  },
  {
    "skill": "Interpretación",
    "name": "Bailar",
    "source": "predator",
    "sourceId": "predator_siren"
  }
]
```

Estas reglas quedan implementadas en:

```text
tools/character_skill_tools.py
tests/test_skill_rules.py
```


## 25. Estado de personaje exportable

`schemas/character-state.schema.json` representa un personaje completo y exportable. Los borradores internos de la interfaz pueden existir durante la creación, pero no deben pasar validación de exportación hasta completar todos los campos obligatorios.

Reglas de estado exportable:

- `exportStatus` debe ser `complete`.
- `creationStatus` debe ser `finalized`.
- Las selecciones principales se guardan por ID, no por nombre visible: `clan.clanId`, `generation.generationId` y `predator.predatorId`.
- Los nombres visibles se derivan desde los catálogos y no son la fuente de verdad.
- Los datos narrativos son obligatorios: nombre, concepto, ambición, deseo, convicciones, toques, biografía y apariencia.
- `domain` es obligatorio. El Dominio personal representa la adaptación individual de la cotería unipersonal y su `pool.baseDots` parte en 1.
- `derived` se guarda junto al estado del personaje. Puede incluir Salud, Voluntad, Humanidad, Potencia de Sangre, presupuestos calculados y datos internos de validación.
- `creationProgress` existe sólo como metadata de UI. No es una regla mecánica.

La estructura principal del estado exportable queda organizada así:

```json
{
  "schemaVersion": "character-state-v17",
  "exportStatus": "complete",
  "creationStatus": "finalized",
  "metadata": {},
  "basics": {},
  "clan": { "clanId": "clan_ventrue" },
  "generation": { "generationId": "generation_decimotercera" },
  "sire": {},
  "predator": { "predatorId": "predator_gato_callejero" },
  "attributes": {},
  "skills": {},
  "specialties": [],
  "disciplines": {},
  "advantages": {},
  "domain": {},
  "convictions": [],
  "touchstones": [],
  "profile": {},
  "derived": {},
  "creationProgress": {}
}
```

El paso 17 define la estructura completa, obligatoria y exportable. El paso 18 cierra los objetos estructurados con `additionalProperties: false`.



## 26. Cierre de propiedades adicionales

`schemas/character-state.schema.json` rechaza propiedades no declaradas en los objetos estructurados del estado exportable. Esto evita errores silenciosos por campos mal escritos, datos basura o extensiones no acordadas.

Regla general:

```json
{
  "additionalProperties": false
}
```

Se aplica a los objetos estructurados del estado exportable, incluyendo:

- raíz del personaje;
- `metadata`;
- `basics`;
- `clan`;
- `generation`;
- `sire`;
- `predator`;
- elementos de `specialties`;
- `disciplines`;
- elementos de poderes;
- `advantages`;
- elementos de méritos y defectos;
- `domain`;
- pool, rasgos, méritos, defectos, contribuciones y trasfondos de Dominio;
- convicciones;
- toques;
- perfil;
- derivados;
- errores y advertencias de validación;
- `creationProgress`.

Excepción documentada:

```text
disciplines.ratings
```

Este objeto se mantiene como mapa dinámico porque sus claves son `disciplineId` del catálogo. La restricción no es libre: las claves deben cumplir el patrón `^[a-z0-9_]+$` y los valores deben ser enteros entre 0 y 5.

`derived.budgets` también quedó estructurado. Debe usar las claves conocidas `advantages` y `domain`; no acepta presupuestos inventados.

`data/creator-data.json` marca esta decisión en `characterStateModel.strictAdditionalProperties = true` y enumera los mapas dinámicos permitidos en `characterStateModel.dynamicMaps`.

Pruebas agregadas:

```text
test_export_schema_closes_structured_objects
test_root_rejects_unknown_properties
test_nested_objects_reject_unknown_properties
test_array_items_reject_unknown_properties
test_derived_budgets_reject_unknown_properties
test_creator_data_marks_character_state_as_strict
```

## 27. Validadores modulares

El paquete separa los validadores de reglas en módulos independientes bajo `tools/validators/`.

Este paso no crea todavía un validador integral. La orquestación completa queda reservada para el paso 20. El objetivo de este paso es que cada área del personaje pueda validarse de forma aislada, testeable y mantenible.

### 27.1 Archivos agregados

```text
tools/__init__.py
tools/validators/__init__.py
tools/validators/common.py
tools/validators/registry.py
tools/validators/attributes.py
tools/validators/skills.py
tools/validators/specialties.py
tools/validators/budget.py
tools/validators/advantages.py
tools/validators/domain.py
tools/validators/disciplines.py
tools/validators/predator.py
tools/validators/validation_rules.py
tools/validators/character_state.py
tests/test_validator_modules.py
```

### 27.2 Módulos

| Módulo | Responsabilidad |
|---|---|
| `attributes` | Valida `attrSequence`, nombres, valores y distribución final de atributos. |
| `skills` | Valida `skillSequence`, nombres, valores y distribución final de habilidades. |
| `specialties` | Valida especialidad gratuita, origen, duplicados normalizados y máximo por habilidad. |
| `budget` | Valida presupuesto de Ventajas y Dominio personal, incluyendo contribuciones reversibles desde Ventajas. |
| `advantages` | Valida méritos y defectos individuales contra `advantagesCatalog`. |
| `domain` | Valida rasgos, trasfondos, méritos, defectos y presupuesto de Dominio personal contra `domainCatalog`. |
| `disciplines` | Valida ratings y poderes seleccionados contra `disciplinas_v5_catalogo.json`. |
| `predator` | Valida el tipo de depredador y sus selecciones directas. |
| `validation_rules` | Valida la estructura declarativa de reglas bloqueantes. |
| `character_state` | Valida el estado exportable contra `character-state.schema.json`. |

### 27.3 Interfaz común

Cada módulo expone una función:

```python
validate(character_state, creator_data, **context) -> list[dict]
```

El resultado siempre es una lista de errores. Una lista vacía significa que ese módulo no encontró errores.

### 27.4 Registro

`tools/validators/registry.py` expone:

```python
list_validators()
get_validator(name)
VALIDATOR_MODULES
```

Este registro permite descubrir los módulos sin convertirlos todavía en un pipeline único.

### 27.5 Límites del paso 27

Los módulos no aplican todavía reglas condicionales como sistema integral. Por ejemplo, el módulo `skills` puede recibir efectos de reglas ya resueltas, pero no decide por sí solo si una regla como `Analfabeto` está activa. Esa evaluación pertenece al validador integral del paso 20.

### 27.6 Metadata en creator-data

`data/creator-data.json` incluye `validatorArchitectureModel`, que documenta qué módulos existen, dónde están y qué responsabilidad tiene cada uno.


## 28. Validador integral de personaje

El validador integral vive en `tools/character_validator.py` y expone dos entradas públicas:

```python
validate_character(character_state, creator_data, **context)
validateCharacter(character_state, creator_data, **context)
```

`validateCharacter` es un alias camelCase para integraciones de interfaz. La función principal recibe el estado completo del personaje, los catálogos base y, opcionalmente, el catálogo de disciplinas, `validation-rules.json` y `character-state.schema.json`.

La salida estable es:

```json
{
  "valid": false,
  "errors": [],
  "warnings": [],
  "derived": {},
  "moduleResults": []
}
```

El pipeline ejecuta los validadores modulares del paso 19 en este orden:

```text
character_state
attributes
skills
specialties
budget
advantages
domain
disciplines
predator
validation_rules
rule_engine
```

`rule_engine` no es un módulo del registro del paso 19. Es la capa integral que aplica `data/validation-rules.json` contra el personaje concreto. Esto separa dos responsabilidades:

```text
validation_rules.py      valida que el archivo de reglas esté bien formado.
character_validator.py   aplica las reglas al estado del personaje.
```

Todas las reglas son bloqueantes. Si una regla se incumple, el validador devuelve `valid: false`.

El validador también recompone `derived` desde las elecciones explícitas del personaje:

```text
derived.health
derived.willpower
derived.humanity
derived.bloodPotency
derived.budgets
derived.validation
```

`derived.validation` guarda una versión sanitizada de errores y advertencias compatible con `character-state.schema.json`. Los errores completos del resultado principal pueden incluir campos adicionales como `module`, `origin`, `traitId`, `domainTraitId` o `actualDots`.

La función acepta `update_derived=True`. En ese modo, el validador escribe los derivados recalculados dentro de `character_state["derived"]`. Esto permite persistir el resultado final antes de exportar.

Regla de diseño: el estado exportable debe validarse mediante `validate_character` antes de ser importado por otra herramienta, bot o plataforma.
