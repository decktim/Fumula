// ============================================================
// STATE
// ============================================================
const state = { ingredients: [], recipes: [], selectedId: null, chart: null };
let editorDraft = null;   // deep-copy of recipe being edited (or blank new one)
let editorMode  = 'new';  // 'new' | 'edit'

// Bootstrap modal handles
let bsIngredientModal, bsRecipeModal, bsPrintModal, bsHelpModal;


// ============================================================
// API HELPERS
// ============================================================
let SERVER_MODE = false;
const LS_KEY = 'fumula_data';

function lsLoad() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || { ingredients: [], recipes: [] }; }
  catch { return { ingredients: [], recipes: [] }; }
}
function lsSave(data) { localStorage.setItem(LS_KEY, JSON.stringify(data)); }

function localApi(method, path, body) {
  const data = lsLoad();

  if (path === '/api/ingredients') {
    if (method === 'GET') return data.ingredients;
    if (method === 'POST') {
      const item = { ...body, id: crypto.randomUUID() };
      data.ingredients.push(item);
      lsSave(data);
      return item;
    }
  }
  const ingMatch = path.match(/^\/api\/ingredients\/(.+)$/);
  if (ingMatch) {
    const id = ingMatch[1];
    if (method === 'PUT') {
      const idx = data.ingredients.findIndex(i => i.id === id);
      if (idx !== -1) { data.ingredients[idx] = { ...body, id }; lsSave(data); return data.ingredients[idx]; }
    }
    if (method === 'DELETE') { data.ingredients = data.ingredients.filter(i => i.id !== id); lsSave(data); return null; }
  }

  if (path === '/api/recipes') {
    if (method === 'GET') return data.recipes;
    if (method === 'POST') {
      const item = { ...body, id: crypto.randomUUID() };
      data.recipes.push(item);
      lsSave(data);
      return item;
    }
  }
  const recMatch = path.match(/^\/api\/recipes\/(.+)$/);
  if (recMatch) {
    const id = recMatch[1];
    if (method === 'PUT') {
      const idx = data.recipes.findIndex(r => r.id === id);
      if (idx !== -1) { data.recipes[idx] = { ...body, id }; lsSave(data); return data.recipes[idx]; }
    }
    if (method === 'DELETE') { data.recipes = data.recipes.filter(r => r.id !== id); lsSave(data); return null; }
  }

  if (path === '/api/import' && method === 'POST') { lsSave(body); return null; }

  throw new Error(`localApi: unhandled ${method} ${path}`);
}

async function api(method, path, body) {
  if (!SERVER_MODE) return localApi(method, path, body);
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status}`);
  if (res.status === 204) return null;
  return res.json();
}

async function loadAll() {
  [state.ingredients, state.recipes] = await Promise.all([
    api('GET', '/api/ingredients'),
    api('GET', '/api/recipes'),
  ]);
}


// ============================================================
// TABS
// ============================================================
function switchTab(name) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('d-none'));
  document.querySelectorAll('#mainTabs .nav-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.remove('d-none');
  document.querySelector(`[data-tab="${name}"]`).classList.add('active');
}


// ============================================================
// INGREDIENTS TAB
// ============================================================
function renderIngredients() {
  const tbody = document.getElementById('ingredients-body');
  tbody.innerHTML = state.ingredients.map(ing => `
    <tr>
      <td>${esc(ing.name)}</td>
      <td>${esc(ing.category)}</td>
      <td>${ing.source_url ? `<a href="${esc(ing.source_url)}" target="_blank">${esc(ing.source_url)}</a>` : ''}</td>
      <td class="text-end">
        <button class="btn btn-outline-secondary btn-sm me-1" onclick="showIngredientModal('${ing.id}')">Edit</button>
        <button class="btn btn-outline-danger btn-sm" onclick="deleteIngredient('${ing.id}')">Delete</button>
      </td>
    </tr>
  `).join('');

  // Populate category datalist
  const cats = [...new Set(state.ingredients.map(i => i.category))];
  document.getElementById('cat-list').innerHTML = cats.map(c => `<option value="${esc(c)}">`).join('');
}

function showIngredientModal(id) {
  const ing = id ? state.ingredients.find(i => i.id === id) : null;
  document.getElementById('ingredientModalTitle').textContent = ing ? 'Edit Ingredient' : 'Add Ingredient';
  document.getElementById('ing-id').value       = ing ? ing.id : '';
  document.getElementById('ing-name').value     = ing ? ing.name : '';
  document.getElementById('ing-category').value = ing ? ing.category : '';
  document.getElementById('ing-url').value      = ing ? ing.source_url : '';
  bsIngredientModal.show();
}

async function saveIngredient() {
  const id   = document.getElementById('ing-id').value;
  const body = {
    name:       document.getElementById('ing-name').value.trim(),
    category:   document.getElementById('ing-category').value.trim().toLowerCase(),
    source_url: document.getElementById('ing-url').value.trim(),
  };
  if (!body.name || !body.category) { alert('Name and Category are required.'); return; }
  if (id) await api('PUT',  `/api/ingredients/${id}`, body);
  else    await api('POST', '/api/ingredients', body);
  await loadAll();
  renderIngredients();
  bsIngredientModal.hide();
}

async function deleteIngredient(id) {
  const ing = state.ingredients.find(i => i.id === id);
  if (!confirm(`Delete '${ing.name}'?`)) return;
  await api('DELETE', `/api/ingredients/${id}`);
  await loadAll();
  renderIngredients();
}


// ============================================================
// RECIPES TAB — LIST + DETAIL
// ============================================================
function renderRecipeList() {
  const el = document.getElementById('recipe-list');
  if (!state.recipes.length) {
    el.innerHTML = '<p class="text-muted small">No recipes yet.</p>';
    return;
  }

  const groupOrder = [];
  const groupMap = {};
  const ungrouped = [];
  for (const r of state.recipes) {
    if (r.group) {
      if (!groupMap[r.group]) { groupMap[r.group] = []; groupOrder.push(r.group); }
      groupMap[r.group].push(r);
    } else {
      ungrouped.push(r);
    }
  }

  let html = '';
  for (const groupName of groupOrder) {
    html += `<div class="recipe-group-header">${esc(groupName)}</div>`;
    html += groupMap[groupName].map(r => recipeListItemHTML(r, true)).join('');
  }
  if (ungrouped.length) {
    if (groupOrder.length) html += `<div class="recipe-group-header">Ungrouped</div>`;
    html += ungrouped.map(r => recipeListItemHTML(r, false)).join('');
  }
  el.innerHTML = html;
}

function recipeListItemHTML(r, indented) {
  const composition = r.categories
    .map(c => `${cap(c.category)} ${c.percentage.toFixed(0)}%`)
    .join(' · ');
  const active = r.id === state.selectedId ? 'active' : '';
  const indent = indented ? ' indented' : '';
  return `
    <div class="recipe-list-item p-2 rounded mb-1${indent} ${active}"
         onclick="selectRecipe('${r.id}')" ondblclick="openEditor(state.recipes.find(r=>r.id==='${r.id}'))">
      <div class="fw-semibold">${esc(r.name)}</div>
      <div class="text-muted small">${esc(composition)}</div>
    </div>`;
}

function selectRecipe(id) {
  state.selectedId = id;
  renderRecipeList();
  const recipe = state.recipes.find(r => r.id === id);
  renderRecipeDetail(recipe);
  if (window.innerWidth < 768) {
    const layout = document.querySelector('.recipes-layout');
    layout.classList.remove('mobile-show-list');
    layout.classList.add('mobile-show-detail');
  }
}

function backToList() {
  const layout = document.querySelector('.recipes-layout');
  layout.classList.remove('mobile-show-detail');
  layout.classList.add('mobile-show-list');
}

function renderRecipeDetail(recipe) {
  const el = document.getElementById('recipe-detail');
  el.innerHTML = `
    <button id="detail-back-btn" class="btn btn-sm btn-outline-secondary mb-3" onclick="backToList()">← Back</button>
    <h4 class="mb-1">${esc(recipe.name)}</h4>
    ${recipe.notes ? `<p class="text-muted mb-3">${esc(recipe.notes)}</p>` : '<p class="mb-3"></p>'}
    <div class="detail-top-section">
      <div class="detail-chart-wrap">
        <canvas id="detail-chart"></canvas>
      </div>
      <div id="detail-legend" class="pt-1"></div>
    </div>
    <div class="mt-4">
      <div class="d-flex align-items-center gap-2 mb-2">
        <label class="form-label mb-0 fw-semibold">Batch size:</label>
        <input type="number" id="detail-multiplier" class="form-control form-control-sm" style="width:90px"
               min="0" step="any" value="10" oninput="updateDetailTable()">
        <span class="text-muted small">g</span>
      </div>
      <table class="table table-sm table-hover align-middle">
        <thead class="table-light">
          <tr><th>Ingredient</th><th>Category</th><th class="text-end">%</th><th class="text-end">Amount</th></tr>
        </thead>
        <tbody id="detail-table-body"></tbody>
      </table>
    </div>`;
  renderChart(recipe);
  updateDetailTable();
}

function updateDetailTable() {
  const recipe = state.recipes.find(r => r.id === state.selectedId);
  if (!recipe) return;
  const multiplier = parseFloat(document.getElementById('detail-multiplier')?.value) || 0;
  const tbody = document.getElementById('detail-table-body');
  if (!tbody) return;
  const rows = [];
  for (const rc of recipe.categories) {
    for (const ri of rc.ingredients) {
      const absPct = rc.percentage * ri.percentage / 100;
      if (absPct <= 0) continue;
      rows.push(`<tr>
        <td>${esc(ingName(ri.ingredient_id))}</td>
        <td>${esc(cap(rc.category))}</td>
        <td class="text-end">${absPct.toFixed(1)}%</td>
        <td class="text-end">${(absPct / 100 * multiplier).toFixed(3)}g</td>
      </tr>`);
    }
  }
  tbody.innerHTML = rows.join('') || '<tr><td colspan="4" class="text-muted text-center">No ingredients</td></tr>';
}

function renderChart(recipe) {
  if (state.chart) { state.chart.destroy(); state.chart = null; }

  const CAT_PALETTES = {
    wood:   ['#8B5E3C','#A0785A','#C4A882','#D4B896','#E8D5B7'],
    resin:  ['#5B4A8A','#7B6AAA','#9B8ACA','#BBAADF','#D4C8EF'],
    binder: ['#2E7D6E','#3E9D8E','#5EBDAE','#8ED8CE','#B8EDE8'],
  };
  const CAT_BASE = Object.fromEntries(Object.entries(CAT_PALETTES).map(([k,v]) => [k, v[0]]));

  const catLabels=[], catPcts=[], catColors=[];
  const ingLabels=[], ingPcts=[], ingColors=[];

  for (const rc of recipe.categories) {
    if (rc.percentage <= 0) continue;
    catLabels.push(cap(rc.category));
    catPcts.push(rc.percentage);
    catColors.push(CAT_BASE[rc.category] ?? '#999');

    const palette = CAT_PALETTES[rc.category] ?? ['#999'];
    const active = rc.ingredients.filter(ri => rc.percentage * ri.percentage / 100 > 0);
    if (active.length) {
      active.forEach((ri, ii) => {
        const abs = rc.percentage * ri.percentage / 100;
        ingLabels.push(ingName(ri.ingredient_id));
        ingPcts.push(abs);
        ingColors.push(palette[ii % palette.length]);
      });
    } else {
      ingLabels.push('');
      ingPcts.push(rc.percentage);
      ingColors.push(CAT_BASE[rc.category] ?? '#ccc');
    }
  }

  const ctx = document.getElementById('detail-chart');
  if (!ctx) return;

  state.chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ingLabels,
      datasets: [
        {
          label: 'Ingredients',
          data: ingPcts,
          backgroundColor: ingColors,
          borderWidth: 1.5,
          borderColor: '#fff',
        },
        {
          label: 'Categories',
          data: catPcts,
          backgroundColor: catColors,
          borderWidth: 1.5,
          borderColor: '#fff',
        },
      ],
    },
    options: {
      animation: false,
      cutout: '30%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: () => [],
            label: ctx => {
              if (ctx.datasetIndex === 0) return ` ${ctx.label}: ${ctx.parsed.toFixed(1)}%`;
              return ` ${catLabels[ctx.dataIndex]}: ${ctx.parsed.toFixed(1)}%`;
            },
          },
        },
      },
    },
  });

  // Custom legend to the right, grouped by category
  const legend = document.getElementById('detail-legend');
  if (!legend) return;
  legend.innerHTML = '';

  // Build per-category ingredient index
  let ingIdx = 0;
  for (let ci = 0; ci < catLabels.length; ci++) {
    const rc = recipe.categories.find(r => cap(r.category) === catLabels[ci]);
    const active = rc ? rc.ingredients.filter(ri => rc.percentage * ri.percentage / 100 > 0) : [];

    // Category row
    const catRow = document.createElement('div');
    catRow.className = 'd-flex align-items-center gap-2 mb-1';
    catRow.innerHTML =
      `<span style="width:13px;height:13px;background:${catColors[ci]};display:inline-block;border-radius:2px;flex-shrink:0"></span>` +
      `<span class="fw-semibold" style="font-size:0.85rem">${esc(catLabels[ci])}</span>` +
      `<span class="text-muted" style="font-size:0.82rem">${catPcts[ci].toFixed(1)}%</span>`;
    legend.appendChild(catRow);

    // Ingredient rows (indented)
    const count = active.length || 1;
    for (let ii = 0; ii < count; ii++) {
      const lbl = ingLabels[ingIdx];
      const pct = ingPcts[ingIdx];
      const col = ingColors[ingIdx];
      ingIdx++;
      if (!lbl) continue;
      const ingRow = document.createElement('div');
      ingRow.className = 'd-flex align-items-center gap-2 mb-1';
      ingRow.style.paddingLeft = '20px';
      ingRow.innerHTML =
        `<span style="width:10px;height:10px;background:${col};display:inline-block;border-radius:2px;flex-shrink:0"></span>` +
        `<span style="font-size:0.8rem">${esc(lbl)}</span>` +
        `<span class="text-muted" style="font-size:0.78rem">${pct.toFixed(1)}%</span>`;
      legend.appendChild(ingRow);
    }

    // Small gap between category groups
    if (ci < catLabels.length - 1) {
      const spacer = document.createElement('div');
      spacer.style.height = '6px';
      legend.appendChild(spacer);
    }
  }
}

function editSelected() {
  if (!state.selectedId) return;
  const recipe = state.recipes.find(r => r.id === state.selectedId);
  if (recipe) openEditor(recipe);
}

async function deleteSelected() {
  if (!state.selectedId) return;
  const recipe = state.recipes.find(r => r.id === state.selectedId);
  if (!recipe || !confirm(`Delete '${recipe.name}'?`)) return;
  await api('DELETE', `/api/recipes/${state.selectedId}`);
  state.selectedId = null;
  await loadAll();
  renderRecipeList();
  document.getElementById('recipe-detail').innerHTML =
    '<p class="text-muted mt-4 text-center">Select a recipe to see details</p>';
  if (window.innerWidth < 768) backToList();
}


async function newVariant() {
  if (!state.selectedId) return;
  const source = state.recipes.find(r => r.id === state.selectedId);
  if (!source) return;

  let groupName = source.group;
  if (!groupName) {
    groupName = source.name;
    await api('PUT', `/api/recipes/${source.id}`, { ...deepCopy(source), group: groupName });
    await loadAll();
    renderRecipeList();
  }

  const clone = deepCopy(source);
  clone.id = null;
  clone.name = source.name + ' (variant)';
  clone.group = groupName;
  openEditor(clone);
}


// ============================================================
// RECIPE EDITOR
// ============================================================
function openEditor(recipe) {
  editorMode  = (recipe?.id) ? 'edit' : 'new';
  editorDraft = recipe ? deepCopy(recipe) : blankRecipe();

  document.getElementById('recipeModalTitle').textContent = (recipe?.id) ? `Edit — ${recipe.name}` : 'New Recipe';
  document.getElementById('editor-name').value  = editorDraft.name;
  document.getElementById('editor-notes').value = editorDraft.notes;
  const groups = [...new Set(state.recipes.filter(r => r.group).map(r => r.group))];
  const sel = document.getElementById('editor-group');
  sel.innerHTML =
    `<option value="">— None —</option>` +
    groups.map(g => `<option value="${esc(g)}" ${editorDraft.group === g ? 'selected' : ''}>${esc(g)}</option>`).join('') +
    `<option value="__new__">+ New group…</option>`;
  if (editorDraft.group && !groups.includes(editorDraft.group)) {
    // group came from a variant clone that doesn't exist yet — treat as new
    sel.value = '__new__';
    document.getElementById('editor-group-new').value = editorDraft.group;
    document.getElementById('editor-group-new').classList.remove('d-none');
  } else {
    document.getElementById('editor-group-new').value = '';
    document.getElementById('editor-group-new').classList.add('d-none');
  }

  renderEditorGroups();
  bsRecipeModal.show();
}

function blankRecipe() {
  const cats = [...new Set(state.ingredients.map(i => i.category))];
  if (!cats.length) cats.push('wood', 'resin', 'binder');
  const n = cats.length;
  const even = Math.round(100 / n * 10) / 10;
  const categories = cats.map((cat, idx) => ({
    category: cat,
    percentage: idx < n - 1 ? even : 0,
    is_auto: idx === n - 1,
    ingredients: [],
  }));
  const autoIdx = categories.findIndex(c => c.is_auto);
  const others = categories.reduce((s, c, i) => i !== autoIdx ? s + c.percentage : s, 0);
  categories[autoIdx].percentage = Math.max(0, 100 - others);
  return { id: null, name: 'New Recipe', notes: '', group: '', categories };
}

function renderEditorGroups() {
  // Category group
  renderPercentageGroup(
    'editor-category-group',
    'categories',
    editorDraft.categories,
    (m) => cap(m.category),
  );

  // Ingredient sections
  const sec = document.getElementById('editor-ingredient-sections');
  sec.innerHTML = '';
  for (const rc of editorDraft.categories) {
    sec.appendChild(buildIngredientSection(rc));
  }
}

function buildIngredientSection(rc) {
  const groupKey = `ing:${rc.category}`;
  const card = document.createElement('div');
  card.className = 'card mb-3';
  card.dataset.category = rc.category;

  const header = document.createElement('div');
  header.className = 'card-header fw-semibold ing-section-header';
  header.dataset.category = rc.category;
  header.textContent = `${cap(rc.category)} Ingredients (${rc.percentage.toFixed(1)}% of batch)`;
  card.appendChild(header);

  const body = document.createElement('div');
  body.className = 'card-body';
  card.appendChild(body);

  // Percentage group (if ingredients exist)
  const groupDiv = document.createElement('div');
  groupDiv.id = `group-${rc.category}`;
  body.appendChild(groupDiv);
  if (rc.ingredients.length) {
    renderPercentageGroup(groupDiv, groupKey, rc.ingredients,
      (m) => ingName(m.ingredient_id));
  } else {
    groupDiv.innerHTML = '<p class="text-muted small">No ingredients added yet.</p>';
  }

  // Add ingredient row
  const available = state.ingredients.filter(
    i => i.category === rc.category && !rc.ingredients.some(ri => ri.ingredient_id === i.id)
  );
  const addRow = document.createElement('div');
  addRow.className = 'd-flex align-items-center gap-2 mt-2';
  if (available.length) {
    const sel = document.createElement('select');
    sel.className = 'form-select form-select-sm';
    sel.style.width = '200px';
    sel.id = `add-sel-${rc.category}`;
    sel.innerHTML = available.map(i => `<option value="${i.id}">${esc(i.name)}</option>`).join('');
    const btn = document.createElement('button');
    btn.className = 'btn btn-outline-secondary btn-sm';
    btn.textContent = 'Add Ingredient';
    btn.onclick = () => addIngredient(rc.category, sel.value);
    addRow.appendChild(sel);
    addRow.appendChild(btn);
  } else {
    addRow.innerHTML = '<span class="text-muted small">All available ingredients added.</span>';
  }
  body.appendChild(addRow);

  // Remove buttons
  if (rc.ingredients.length) {
    const remRow = document.createElement('div');
    remRow.className = 'd-flex flex-wrap gap-1 mt-2';
    rc.ingredients.forEach(ri => {
      const btn = document.createElement('button');
      btn.className = 'btn btn-sm btn-outline-danger';
      btn.textContent = `✕ ${ingName(ri.ingredient_id)}`;
      btn.onclick = () => removeIngredient(rc.category, ri.ingredient_id);
      remRow.appendChild(btn);
    });
    body.appendChild(remRow);
  }

  return card;
}

function addIngredient(category, ingredientId) {
  const rc = editorDraft.categories.find(c => c.category === category);
  if (!rc) return;
  if (rc.ingredients.length === 0) {
    rc.ingredients.push({ ingredient_id: ingredientId, percentage: 100, is_auto: true });
  } else {
    rc.ingredients.push({ ingredient_id: ingredientId, percentage: 0, is_auto: false });
    if (!rc.ingredients.some(ri => ri.is_auto)) rc.ingredients[rc.ingredients.length - 1].is_auto = true;
  }
  rerenderIngredientSection(category);
}

function removeIngredient(category, ingredientId) {
  const rc = editorDraft.categories.find(c => c.category === category);
  if (!rc) return;
  rc.ingredients = rc.ingredients.filter(ri => ri.ingredient_id !== ingredientId);
  if (rc.ingredients.length && !rc.ingredients.some(ri => ri.is_auto))
    rc.ingredients[rc.ingredients.length - 1].is_auto = true;
  rerenderIngredientSection(category);
}

function rerenderIngredientSection(category) {
  const rc = editorDraft.categories.find(c => c.category === category);
  const sec = document.getElementById('editor-ingredient-sections');
  const oldCard = sec.querySelector(`[data-category="${category}"]`);
  const newCard = buildIngredientSection(rc);
  if (oldCard) sec.replaceChild(newCard, oldCard);
  else sec.appendChild(newCard);
}

// ---- Percentage group renderer ----------------------------------------

function renderPercentageGroup(containerOrId, groupKey, members, labelFn) {
  const container = typeof containerOrId === 'string'
    ? document.getElementById(containerOrId)
    : containerOrId;
  if (!container) return;
  const autoIdx = members.findIndex(m => m.is_auto);

  container.innerHTML = members.map((m, i) => {
    const isAuto = i === autoIdx;
    const label  = esc(labelFn(m, i));
    const pct    = m.percentage.toFixed(1);
    return `
      <div class="d-flex align-items-center mb-2">
        <input type="radio" class="form-check-input me-2 auto-radio flex-shrink-0"
               name="auto-${groupKey}" value="${i}"
               ${isAuto ? 'checked' : ''}
               data-group="${groupKey}" data-idx="${i}">
        <span class="auto-icon me-2 flex-shrink-0 ${isAuto ? 'text-primary' : 'text-muted'}"
              data-group="${groupKey}" data-idx="${i}">⟳</span>
        <span class="me-3 flex-shrink-0 label-col" title="${label}">${label}</span>
        <input type="range" min="0" max="100" step="0.1" value="${pct}"
               class="flex-grow-1 pct-slider"
               data-group="${groupKey}" data-idx="${i}"
               ${isAuto ? 'disabled' : ''}>
        <input type="number" min="0" max="100" step="0.1" value="${pct}"
               class="form-control ms-2 pct-entry" style="width:80px"
               data-group="${groupKey}" data-idx="${i}"
               ${isAuto ? 'readonly' : ''}>
        <span class="ms-1">%</span>
      </div>`;
  }).join('');

  container.querySelectorAll('.pct-slider').forEach(el => el.addEventListener('input',  onSliderInput));
  container.querySelectorAll('.pct-entry').forEach(el  => el.addEventListener('change', onEntryChange));
  container.querySelectorAll('.auto-radio').forEach(el => el.addEventListener('change', onRadioChange));
}

// ---- Event handlers -------------------------------------------------------

function getMembers(groupKey) {
  if (groupKey === 'categories') return editorDraft.categories;
  const cat = groupKey.slice(4); // strip "ing:"
  return editorDraft.categories.find(c => c.category === cat).ingredients;
}

function computeMax(members, autoIdx, idx) {
  const others = members.reduce((s, m, i) => (i !== autoIdx && i !== idx) ? s + m.percentage : s, 0);
  return Math.max(0, 100 - others);
}

function recalcAuto(members) {
  const autoIdx = members.findIndex(m => m.is_auto);
  const others  = members.reduce((s, m, i) => i !== autoIdx ? s + m.percentage : s, 0);
  members[autoIdx].percentage = Math.round(Math.max(0, 100 - others) * 10) / 10;
  return autoIdx;
}

function syncAutoWidgets(groupKey, members, autoIdx) {
  const val = members[autoIdx].percentage;
  const slider = document.querySelector(`.pct-slider[data-group="${groupKey}"][data-idx="${autoIdx}"]`);
  const entry  = document.querySelector(`.pct-entry[data-group="${groupKey}"][data-idx="${autoIdx}"]`);
  if (slider) slider.value = val;
  if (entry)  entry.value  = val.toFixed(1);
  updateIngHeaderLabels();
}

function onSliderInput(e) {
  const groupKey = e.target.dataset.group;
  const idx      = parseInt(e.target.dataset.idx);
  const members  = getMembers(groupKey);
  const autoIdx  = members.findIndex(m => m.is_auto);

  let val = Math.round(parseFloat(e.target.value) * 10) / 10;
  val = Math.min(val, computeMax(members, autoIdx, idx));
  e.target.value = val;
  members[idx].percentage = val;

  const entry = document.querySelector(`.pct-entry[data-group="${groupKey}"][data-idx="${idx}"]`);
  if (entry) entry.value = val.toFixed(1);

  const newAutoIdx = recalcAuto(members);
  syncAutoWidgets(groupKey, members, newAutoIdx);
}

function onEntryChange(e) {
  const groupKey = e.target.dataset.group;
  const idx      = parseInt(e.target.dataset.idx);
  const members  = getMembers(groupKey);
  const autoIdx  = members.findIndex(m => m.is_auto);

  let val = parseFloat(e.target.value);
  if (isNaN(val)) { e.target.value = members[idx].percentage.toFixed(1); return; }
  val = Math.max(0, Math.min(computeMax(members, autoIdx, idx), Math.round(val * 10) / 10));
  e.target.value = val.toFixed(1);
  members[idx].percentage = val;

  const slider = document.querySelector(`.pct-slider[data-group="${groupKey}"][data-idx="${idx}"]`);
  if (slider) slider.value = val;

  const newAutoIdx = recalcAuto(members);
  syncAutoWidgets(groupKey, members, newAutoIdx);
}

function onRadioChange(e) {
  const groupKey  = e.target.dataset.group;
  const newAuto   = parseInt(e.target.value);
  const members   = getMembers(groupKey);

  members.forEach((m, i) => m.is_auto = i === newAuto);

  // Update disabled / readonly / icon states without re-rendering
  members.forEach((m, i) => {
    const slider = document.querySelector(`.pct-slider[data-group="${groupKey}"][data-idx="${i}"]`);
    const entry  = document.querySelector(`.pct-entry[data-group="${groupKey}"][data-idx="${i}"]`);
    const icon   = document.querySelector(`.auto-icon[data-group="${groupKey}"][data-idx="${i}"]`);
    const isAuto = i === newAuto;
    if (slider) slider.disabled  = isAuto;
    if (entry)  entry.readOnly   = isAuto;
    if (icon) {
      icon.classList.toggle('text-primary', isAuto);
      icon.classList.toggle('text-muted', !isAuto);
    }
  });

  const autoIdx = recalcAuto(members);
  syncAutoWidgets(groupKey, members, autoIdx);
}

function updateIngHeaderLabels() {
  editorDraft.categories.forEach(rc => {
    const el = document.querySelector(`.ing-section-header[data-category="${rc.category}"]`);
    if (el) el.textContent = `${cap(rc.category)} Ingredients (${rc.percentage.toFixed(1)}% of batch)`;
  });
}

// ---- Group select ---------------------------------------------------------

function onGroupSelectChange() {
  const isNew = document.getElementById('editor-group').value === '__new__';
  document.getElementById('editor-group-new').classList.toggle('d-none', !isNew);
  if (isNew) document.getElementById('editor-group-new').focus();
}

// ---- Save -----------------------------------------------------------------

async function saveRecipe() {
  const name = document.getElementById('editor-name').value.trim();
  if (!name) { alert('Recipe name is required.'); return; }
  editorDraft.name  = name;
  editorDraft.notes = document.getElementById('editor-notes').value.trim();
  const groupSel = document.getElementById('editor-group').value;
  editorDraft.group = groupSel === '__new__'
    ? document.getElementById('editor-group-new').value.trim()
    : groupSel;

  if (editorMode === 'edit') {
    await api('PUT', `/api/recipes/${editorDraft.id}`, editorDraft);
  } else {
    await api('POST', '/api/recipes', editorDraft);
  }

  await loadAll();
  renderRecipeList();

  // Refresh detail panel if the saved recipe is still selected
  const saved = state.recipes.find(r => r.name === editorDraft.name) ??
                state.recipes.find(r => r.id === editorDraft.id);
  if (saved) { state.selectedId = saved.id; selectRecipe(saved.id); }

  bsRecipeModal.hide();
}


// ============================================================
// PRINT
// ============================================================
function showPrintDialog() {
  const el = document.getElementById('print-recipe-list');
  el.innerHTML = state.recipes.map(r => `
    <div class="form-check">
      <input class="form-check-input" type="checkbox" id="pr-${r.id}" value="${r.id}" checked>
      <label class="form-check-label" for="pr-${r.id}">${esc(r.name)}</label>
    </div>`).join('');
  bsPrintModal.show();
}

function buildPrintChartSVG(recipe) {
  // Collect ingredient slices in category order
  const slices = [];
  for (const rc of recipe.categories) {
    const active = rc.ingredients.filter(ri => rc.percentage * ri.percentage / 100 > 0);
    for (const ri of active) {
      slices.push({ name: ingName(ri.ingredient_id), category: rc.category, pct: rc.percentage * ri.percentage / 100 });
    }
  }
  if (!slices.length) return '';

  // Evenly spaced gray shades from dark to light
  const n = slices.length;
  const shades = slices.map((_, i) => {
    const v = Math.round(15 + (i / Math.max(n - 1, 1)) * 70);
    const h = Math.round(v * 2.55).toString(16).padStart(2, '0');
    return `#${h}${h}${h}`;
  });

  // SVG donut
  const cx = 80, cy = 80, outerR = 74, innerR = 37, svgSize = 160;
  function polar(r, deg) {
    const rad = (deg - 90) * Math.PI / 180;
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
  }
  function arcPath(a1, a2) {
    const [x1, y1] = polar(outerR, a1), [x2, y2] = polar(outerR, a2);
    const [x3, y3] = polar(innerR, a2), [x4, y4] = polar(innerR, a1);
    const lg = (a2 - a1) > 180 ? 1 : 0;
    return `M${x1},${y1} A${outerR},${outerR} 0 ${lg} 1 ${x2},${y2} L${x3},${y3} A${innerR},${innerR} 0 ${lg} 0 ${x4},${y4} Z`;
  }

  let paths = '', angle = 0;
  slices.forEach((sl, i) => {
    const end = angle + sl.pct / 100 * 360;
    paths += `<path d="${arcPath(angle, end)}" fill="${shades[i]}" stroke="#fff" stroke-width="1.5"/>`;
    angle = end;
  });

  const svg = `<svg width="${svgSize}" height="${svgSize}" viewBox="0 0 ${svgSize} ${svgSize}" xmlns="http://www.w3.org/2000/svg">${paths}</svg>`;

  // Legend: iterate slices directly so shades[i] is always in sync with the SVG
  let legendHtml = '', lastCat = null;
  slices.forEach((sl, i) => {
    if (sl.category !== lastCat) {
      if (lastCat !== null) legendHtml += `<div style="height:6px"></div>`;
      const rc = recipe.categories.find(c => c.category === sl.category);
      legendHtml += `<div style="font-size:10px;font-weight:600;margin-bottom:4px;">${esc(cap(sl.category))} ${rc ? rc.percentage.toFixed(1) : ''}%</div>`;
      lastCat = sl.category;
    }
    legendHtml +=
      `<div style="display:flex;align-items:center;gap:5px;padding-left:10px;font-size:9.5px;margin-bottom:3px;">` +
      `<span style="width:11px;height:11px;background:${shades[i]};display:inline-block;border:1px solid #888;flex-shrink:0;print-color-adjust:exact;-webkit-print-color-adjust:exact"></span>` +
      `<span>${esc(sl.name)}</span>&nbsp;<span style="color:#555">${sl.pct.toFixed(1)}%</span></div>`;
  });

  return `<div style="display:flex;align-items:center;gap:12px;">${svg}<div style="font-family:Georgia,serif;">${legendHtml}</div></div>`;
}

function generatePrint() {
  const selected = [...document.querySelectorAll('#print-recipe-list input:checked')]
    .map(cb => state.recipes.find(r => r.id === cb.value))
    .filter(Boolean);
  if (!selected.length) { alert('Select at least one recipe.'); return; }

  const rawGrams = document.getElementById('print-grams').value;
  const grams = rawGrams.split(',').map(s => parseFloat(s.trim())).filter(g => !isNaN(g) && g > 0);
  if (!grams.length) { alert('Enter valid target grams.'); return; }

  const gramCols = grams.map(g => `<th>${g}g</th>`).join('');
  const tables = selected.map(recipe => {
    const rows = [];
    for (const rc of recipe.categories) {
      for (const ri of rc.ingredients) {
        const absPct = rc.percentage * ri.percentage / 100;
        if (absPct <= 0) continue;
        const amounts = grams.map(g => `<td>${(absPct / 100 * g).toFixed(3)}</td>`).join('');
        rows.push(`<tr><td>${esc(ingName(ri.ingredient_id))}</td><td>${esc(cap(rc.category))}</td><td>${absPct.toFixed(1)}%</td>${amounts}</tr>`);
      }
    }
    return `
      <div class="recipe-block">
        <h2>${esc(recipe.name)}</h2>
        ${recipe.notes ? `<p class="notes">${esc(recipe.notes)}</p>` : ''}
        <div style="display:flex;align-items:stretch;gap:24px;">
          <table style="align-self:flex-start">
            <thead><tr><th>Ingredient</th><th>Category</th><th>% of Batch</th>${gramCols}</tr></thead>
            <tbody>${rows.join('')}</tbody>
          </table>
          ${buildPrintChartSVG(recipe)}
        </div>
      </div>`;
  }).join('');

  const css = `
    body { font-family: Georgia, serif; margin: 20px; }
    h2 { font-size: 1.1em; margin-bottom: 4px; }
    .notes { color: #666; font-style: italic; font-size: .9em; }
    .recipe-block { margin-bottom: 40px; }
    table { border-collapse: collapse; }
    th, td { border: 1px solid #aaa; padding: 5px 10px; text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    th:nth-child(2), td:nth-child(2) { text-align: center; }
    th { background: #f0f0f0; }
    * { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    @media print { body { margin: 0; } }`;

  const win = window.open('', '_blank');
  win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Recipe Sheet</title><style>${css}</style></head><body>${tables}</body></html>`);
  win.document.close();
  win.focus();
  win.print();
  bsPrintModal.hide();
}


// ============================================================
// IMPORT / EXPORT
// ============================================================
async function exportData() {
  const json = JSON.stringify({ ingredients: state.ingredients, recipes: state.recipes }, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  if (navigator.share) {
    const file = new File([blob], 'incense_data.json', { type: 'application/json' });
    try {
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: 'incense_data.json' });
      } else {
        await navigator.share({ title: 'incense_data.json', text: json });
      }
      return;
    } catch (e) {
      if (e.name === 'AbortError') return;
    }
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'incense_data.json';
  a.click();
}

async function importData(input) {
  const file = input.files[0];
  if (!file) return;
  input.value = '';
  const text = await file.text();
  let data;
  try { data = JSON.parse(text); } catch { alert('Invalid JSON file.'); return; }
  if (!data.ingredients || !data.recipes) { alert('File missing ingredients or recipes.'); return; }
  await api('POST', '/api/import', data);
  state.ingredients = data.ingredients;
  state.recipes = data.recipes;
  state.selectedId = null;
  renderIngredients();
  renderRecipeList();
  document.getElementById('recipe-detail').innerHTML = '<p class="text-muted mt-4 text-center">Select a recipe to see details</p>';
}

// ============================================================
// UTILITIES
// ============================================================
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }
function ingName(id) {
  return state.ingredients.find(i => i.id === id)?.name ?? '(unknown)';
}
function deepCopy(obj) { return JSON.parse(JSON.stringify(obj)); }


// ============================================================
// DEFAULTS / RESET
// ============================================================
async function loadDefaults() {
  if (!confirm('Load defaults? This will replace all your current data.')) return;
  try {
    const d = await fetch('/api/defaults').then(r => r.json());
    lsSave(d);
    state.selectedId = null;
    await loadAll();
    renderIngredients();
    renderRecipeList();
    document.getElementById('recipe-detail').innerHTML =
      '<p class="text-muted mt-4 text-center">Select a recipe to see details</p>';
  } catch { alert('Failed to load defaults.'); }
}

async function resetData() {
  if (!confirm('Reset all data? This cannot be undone.')) return;
  if (SERVER_MODE) {
    await api('POST', '/api/import', { ingredients: [], recipes: [] });
  } else {
    lsSave({ ingredients: [], recipes: [] });
  }
  state.selectedId = null;
  await loadAll();
  renderIngredients();
  renderRecipeList();
  document.getElementById('recipe-detail').innerHTML =
    '<p class="text-muted mt-4 text-center">Select a recipe to see details</p>';
}


// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  bsIngredientModal = new bootstrap.Modal(document.getElementById('ingredientModal'));
  bsRecipeModal     = new bootstrap.Modal(document.getElementById('recipeModal'));
  bsPrintModal      = new bootstrap.Modal(document.getElementById('printModal'));
  bsHelpModal       = new bootstrap.Modal(document.getElementById('helpModal'));

  // Tab switching
  document.querySelectorAll('#mainTabs .nav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      switchTab(link.dataset.tab);
    });
  });

  let hasDefaults = false;
  try {
    const cfg = await fetch('/api/config').then(r => r.json());
    SERVER_MODE = cfg.server_mode;
    hasDefaults = cfg.has_defaults;
  } catch { SERVER_MODE = false; }

  // In localStorage mode: auto-load defaults on first visit
  if (!SERVER_MODE && !localStorage.getItem(LS_KEY)) {
    try {
      // Try API first (Flask running), then fall back to static file (PWA offline)
      const url = hasDefaults ? '/api/defaults' : './defaults.json';
      const d = await fetch(url).then(r => r.ok ? r.json() : Promise.reject());
      lsSave(d);
    } catch {}
  }

  // Show/hide defaults button
  const defaultsBtn = document.getElementById('btn-load-defaults');
  if (defaultsBtn) defaultsBtn.classList.toggle('d-none', SERVER_MODE || !hasDefaults);
  const resetBtn = document.getElementById('btn-reset-data');
  if (resetBtn) resetBtn.classList.toggle('d-none', SERVER_MODE);

  await loadAll();
  renderIngredients();
  renderRecipeList();

  // Initialize mobile master-detail state
  if (window.innerWidth < 768) {
    document.querySelector('.recipes-layout').classList.add('mobile-show-list');
  }
});
