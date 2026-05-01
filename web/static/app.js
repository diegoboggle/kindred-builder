const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

let catalogs = null;
const attributeValues = [4, 1, 3, 3, 3];
const skillValues = [4, 3, 3, 3, 2, 2, 2, 1, 1, 1];

function normalizeIdentifier(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[:\-]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .join('_');
}

function option(value, label, selected = false) {
  const el = document.createElement('option');
  el.value = value;
  el.textContent = label;
  el.selected = selected;
  return el;
}

function fillSelect(select, items, getValue, getLabel, selectedValue) {
  select.innerHTML = '';
  for (const item of items) select.appendChild(option(getValue(item), getLabel(item), getValue(item) === selectedValue));
}

function predator() {
  return catalogs.predators.find((item) => item.id === $('#predatorSelect').value) || catalogs.predators[0];
}

function selectedPredatorDisciplineId() {
  return normalizeIdentifier($('#predatorDisciplineSelect').value || predator()?.disciplineChoices?.[0] || 'Celeridad');
}

function parseSpecialty(raw) {
  const [skill, ...rest] = String(raw || '').split(':');
  return { skill: skill.trim(), name: rest.join(':').trim() || 'General' };
}

function buildSequence(container, names, values, defaults) {
  container.innerHTML = '';
  values.forEach((value, index) => {
    const label = document.createElement('label');
    label.textContent = `${index + 1}. ${value} punto${value > 1 ? 's' : ''}`;
    const select = document.createElement('select');
    select.dataset.sequence = container.id;
    select.dataset.index = String(index);
    fillSelect(select, names, (x) => x, (x) => x, defaults[index]);
    select.addEventListener('change', () => buildStateIntoTextarea());
    label.appendChild(select);
    container.appendChild(label);
  });
}

function refreshPredatorChoices() {
  const p = predator();
  fillSelect($('#predatorDisciplineSelect'), p.disciplineChoices || [], (x) => x, (x) => x, p.disciplineChoices?.[0]);
  fillSelect($('#predatorSpecialtySelect'), p.specialtyChoices || [], (x) => x, (x) => x, p.specialtyChoices?.[0]);
  refreshPowers();
}

function refreshPowers() {
  const disciplineId = selectedPredatorDisciplineId();
  const powers = catalogs.powers.filter((power) => power.disciplineId === disciplineId && power.level <= 1 && !power.amalgamRequirement);
  fillSelect($('#powerSelect'), powers, (x) => x.id, (x) => `${x.name} (${x.discipline} ${x.level})`, powers[0]?.id);
}

function selectedValues(containerId) {
  return $$(`#${containerId} select`).map((select) => select.value);
}

function buildMap(names, sequence, values, fallback) {
  const result = Object.fromEntries(names.map((name) => [name, fallback]));
  sequence.forEach((name, index) => { if (name) result[name] = values[index]; });
  return result;
}

function buildSpecialties(skills, freeSkill, freeName, predatorSpecialty) {
  const result = [{ skill: freeSkill, name: freeName, source: 'free' }];
  const used = new Set([`${freeSkill}::${freeName}`.toLowerCase()]);
  const predKey = `${predatorSpecialty.skill}::${predatorSpecialty.name}`.toLowerCase();
  if (skills[predatorSpecialty.skill] > 0 && !used.has(predKey)) {
    result.push({ skill: predatorSpecialty.skill, name: predatorSpecialty.name, source: 'predator' });
    used.add(predKey);
  }
  for (const skill of catalogs.specialRequiredSkills) {
    if (skills[skill] > 0 && !result.some((item) => item.skill === skill)) {
      result.push({ skill, name: 'General', source: 'manual' });
    }
  }
  return result;
}

function buildState() {
  const form = new FormData($('#creatorForm'));
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const attrSequence = selectedValues('attributeSequence');
  const skillSequence = selectedValues('skillSequence');
  const attributes = buildMap(catalogs.attributes, attrSequence, attributeValues, 2);
  const skills = buildMap(catalogs.skills, skillSequence, skillValues, 0);
  const freeSpecialtySkill = form.get('freeSpecialtySkill');
  const freeSpecialtyName = String(form.get('freeSpecialtyName') || '').trim() || 'General';
  const predatorSpecialty = parseSpecialty(form.get('predatorSpecialty'));
  const disciplineId = selectedPredatorDisciplineId();
  const powerId = form.get('powerId');
  const selectedPower = catalogs.powers.find((power) => power.id === powerId);
  const chasse = Number(form.get('chasse') || 0);
  const lien = Number(form.get('lien') || 0);
  const portillon = Number(form.get('portillon') || 0);
  const domainSpent = chasse + lien + portillon;

  return {
    schemaVersion: 'character-state-v17',
    exportStatus: 'complete',
    creationStatus: 'finalized',
    metadata: {
      characterId: `character_ui_${Date.now()}`,
      createdAt: now,
      updatedAt: now,
      appVersion: 'test-ui',
      exportedAt: now,
    },
    discordId: String(form.get('discordId') || '').trim(),
    basics: {
      name: String(form.get('name') || '').trim(),
      concept: String(form.get('concept') || '').trim(),
      ambition: String(form.get('ambition') || '').trim(),
      desire: String(form.get('desire') || '').trim(),
    },
    clan: { clanId: form.get('clanId') },
    generation: { generationId: form.get('generationId'), bloodPotencyBase: 1 },
    sire: { status: form.get('sireStatus') },
    predator: {
      predatorId: form.get('predatorId'),
      selectedDisciplineId: disciplineId,
      selectedSpecialty: predatorSpecialty,
      automaticAwardsApplied: true,
    },
    attrSequence,
    attributes,
    skillSequence,
    skills,
    freeSpecialtySkill,
    freeSpecialtyName,
    specialties: buildSpecialties(skills, freeSpecialtySkill, freeSpecialtyName, predatorSpecialty),
    disciplines: {
      ratings: { [disciplineId]: 1 },
      powers: selectedPower ? [{ recordId: selectedPower.id, disciplineId: selectedPower.disciplineId, source: 'creation' }] : [],
    },
    advantages: {
      merits: [],
      flaws: [],
      budget: {
        totalMeritDots: 7,
        spentMeritDots: 0,
        contributedToDomainDots: 0,
        availableMeritDots: 7,
        totalFlawDots: 0,
        spentFlawDots: 0,
        receivedFromDomainDots: 0,
      },
    },
    domain: {
      enabled: true,
      pool: { baseDots: 1, contributedAdvantageDots: 0, flawDots: 0, grantedDots: 0, spentDots: domainSpent },
      traits: { chasse, lien, portillon },
      merits: [],
      flaws: [],
      contributions: [],
      backgrounds: [],
    },
    convictions: [{ id: 'conviction_001', text: String(form.get('conviction') || '').trim(), touchstoneId: 'touchstone_001' }],
    touchstones: [{
      id: 'touchstone_001',
      name: String(form.get('touchstoneName') || '').trim(),
      relationship: String(form.get('touchstoneRelationship') || '').trim(),
      description: String(form.get('touchstoneDescription') || '').trim(),
      linkedConvictionId: 'conviction_001',
    }],
    profile: {
      biography: String(form.get('biography') || '').trim(),
      appearance: String(form.get('appearance') || '').trim(),
    },
    derived: {
      health: { max: (attributes.Resistencia || 0) + 3, current: (attributes.Resistencia || 0) + 3 },
      willpower: { max: (attributes.Compostura || 0) + (attributes.Resolución || 0), current: (attributes.Compostura || 0) + (attributes.Resolución || 0) },
      humanity: 7,
      bloodPotency: 1,
      budgets: { advantages: { availableMeritDots: 7 }, domain: { availableDots: Math.max(0, 1 - domainSpent) } },
      validation: { valid: false, errors: [], warnings: [], lastValidatedAt: now },
    },
    creationProgress: {
      currentStep: 'summary',
      completedSteps: ['welcome', 'clan', 'sire', 'identity', 'predator', 'attributes', 'skills', 'disciplines', 'advantages', 'convictions', 'profile'],
      uiOnly: true,
    },
  };
}

function buildStateIntoTextarea() {
  $('#stateJson').value = JSON.stringify(buildState(), null, 2);
}

function readStateFromTextarea() {
  return JSON.parse($('#stateJson').value);
}

function renderValidation(result) {
  const status = $('#status');
  status.className = `status ${result.valid ? 'ok' : 'bad'}`;
  status.textContent = result.valid ? 'Válido para exportar' : `${result.errors?.length || 0} error(es)`;
  $('#derived').textContent = JSON.stringify(result.derived || {}, null, 2);

  const errors = result.errors || [];
  if (!errors.length) {
    $('#errors').className = 'result-list muted';
    $('#errors').textContent = 'Sin errores bloqueantes.';
    return;
  }
  $('#errors').className = 'result-list';
  $('#errors').innerHTML = errors.map((error) => `
    <div class="error-card">
      <strong>${error.code || 'error'}</strong>
      <span>${error.message || ''}</span>
      ${error.path ? `<div><code>${error.path}</code></div>` : ''}
      ${error.module ? `<small>Módulo: ${error.module}</small>` : ''}
    </div>
  `).join('');
}

async function postJson(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function validate(path = '/api/validate') {
  const result = await postJson(path, readStateFromTextarea());
  renderValidation(result);
  if (result.characterState) $('#stateJson').value = JSON.stringify(result.characterState, null, 2);
}

function downloadJson() {
  const blob = new Blob([$('#stateJson').value], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'character-state.json';
  link.click();
  URL.revokeObjectURL(link.href);
}

async function init() {
  catalogs = await fetch('/api/catalogs').then((response) => response.json());
  fillSelect($('#clanSelect'), catalogs.clans, (x) => x.id, (x) => x.name, 'clan_ventrue');
  fillSelect($('#generationSelect'), catalogs.generations, (x) => x.id, (x) => x.name, 'generation_decimotercera');
  fillSelect($('#predatorSelect'), catalogs.predators, (x) => x.id, (x) => x.name, 'predator_gato_callejero');
  fillSelect($('#freeSpecialtySkill'), catalogs.skills, (x) => x, (x) => x, 'Academicismo');
  buildSequence($('#attributeSequence'), catalogs.attributes, attributeValues, ['Fuerza', 'Resolución', 'Destreza', 'Resistencia', 'Carisma']);
  buildSequence($('#skillSequence'), catalogs.skills, skillValues, ['Academicismo', 'Armas de Fuego', 'Artesanía', 'Atletismo', 'Callejeo', 'Ciencias', 'Conducir', 'Consciencia', 'Etiqueta', 'Finanzas']);
  refreshPredatorChoices();
  buildStateIntoTextarea();

  $('#predatorSelect').addEventListener('change', () => { refreshPredatorChoices(); buildStateIntoTextarea(); });
  $('#predatorDisciplineSelect').addEventListener('change', () => { refreshPowers(); buildStateIntoTextarea(); });
  $('#creatorForm').addEventListener('input', buildStateIntoTextarea);
  $('#creatorForm').addEventListener('change', buildStateIntoTextarea);
  $('#buildBtn').addEventListener('click', buildStateIntoTextarea);
  $('#validateBtn').addEventListener('click', () => validate('/api/validate'));
  $('#finalizeBtn').addEventListener('click', () => validate('/api/finalize'));
  $('#downloadBtn').addEventListener('click', downloadJson);
}

init().catch((error) => {
  $('#status').className = 'status bad';
  $('#status').textContent = 'Error al iniciar';
  $('#errors').textContent = error.message;
});
