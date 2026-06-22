const API = '/v1/webui';
const ROUTES = {
  context: '/v1/webui/context',
  memories: '/v1/webui/memories',
  memorySpaces: '/v1/webui/memory-spaces',
  workspaces: '/v1/webui/workspaces',
  config: '/v1/webui/config',
  services: '/v1/webui/services',
  embeddingStatus: '/v1/webui/embedding/status',
  embeddingMaintenance: '/v1/webui/embedding/maintenance',
  embeddingRefresh: '/v1/webui/embedding/refresh',
  embeddingJobs: '/v1/webui/embedding/jobs',
  devStatus: '/v1/webui/dev/status',
  devSeedingStatus: '/v1/webui/dev/seeding/status',
  devSeedingInit: '/v1/webui/dev/seeding/init',
  devSeedingReset: '/v1/webui/dev/seeding/reset',
  devEval: '/v1/webui/dev/eval',
  devOptimizeThreshold: '/v1/webui/dev/optimize-threshold',
  graph: '/v1/webui/graph',
  diagnostics: '/v1/webui/diagnostics',
  logs: '/v1/webui/logs',
};

const state = {
  context: null,
  selectedMemory: null,
  selectedWorkspace: null,
  selectedService: 'api',
  selectedEmbeddingJob: null,
  graphData: null,
  diagnosticsBundle: null,
  logSummary: null,
  logTailLines: 80,
  lastResponse: null,
};

function $(id) {
  return document.getElementById(id);
}

function showMessage(message, kind = 'info') {
  const el = $('status-message');
  if (!el) return;
  el.textContent = message;
  el.dataset.kind = kind;
}

function renderJson(id, value) {
  const el = $(id);
  if (el) el.textContent = JSON.stringify(value, null, 2);
}

function renderText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function parseMaybeJson(value) {
  if (value == null) return null;
  const text = String(value).trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function safeTailLines(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 80;
  return clamp(Math.trunc(parsed), 10, 500);
}

function currentTailLines() {
  const input = $('log-tail-lines');
  const lines = safeTailLines(input?.value ?? state.logTailLines);
  state.logTailLines = lines;
  if (input) input.value = String(lines);
  return lines;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { Accept: 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();
  state.lastResponse = { status: response.status, payload, path };
  if (!response.ok) {
    const message =
      payload && payload.error && payload.error.message
        ? payload.error.message
        : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

function selectTab(name) {
  document.querySelectorAll('.tab-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === name);
  });
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `tab-${name}`);
  });
}

function wireTabs() {
  document.querySelectorAll('.tab-button').forEach((button) => {
    button.addEventListener('click', () => selectTab(button.dataset.tab));
  });
}

function memorySpaceKeyFromForm(form) {
  const value = form.querySelector('[name="memory_space_key"]')?.value?.trim();
  return value || state.context?.config?.safe_paths?.default_memory_space_key || '';
}

function normalizeMemoryEntry(entry) {
  const memory = entry?.memory && typeof entry.memory === 'object' ? entry.memory : entry;
  return {
    memory,
    score: typeof entry?.score === 'number' ? entry.score : null,
    rank: typeof entry?.rank === 'number' ? entry.rank : null,
    matchedText: typeof entry?.matched_text === 'string' ? entry.matched_text : null,
    snippet: typeof entry?.snippet === 'string' ? entry.snippet : null,
    chunkIndex: typeof entry?.chunk_index === 'number' ? entry.chunk_index : null,
  };
}

function renderMemoryList(memories) {
  const root = $('memory-results');
  if (!root) return;
  if (!memories.length) {
    root.innerHTML = '<div class="empty">No memories found.</div>';
    return;
  }
  root.innerHTML = memories
    .map((entry) => {
      const { memory, score, rank, matchedText, snippet, chunkIndex } = normalizeMemoryEntry(entry);
      const memoryId = memory?.id || '';
      const details = [memory?.space, memory?.type, memory?.status || 'active'].filter(Boolean);
      if (rank !== null) details.push(`rank ${rank}`);
      if (score !== null) details.push(`score ${score.toFixed(3)}`);
      if (chunkIndex !== null) details.push(`chunk ${chunkIndex}`);
      const preview = snippet || matchedText || memory?.content || '';
      return `
        <button class="list-item" data-memory-id="${escapeHtml(memoryId)}">
          <strong>${escapeHtml(memoryId || 'unknown memory')}</strong>
          <span>${escapeHtml(details.join(' · '))}</span>
          <small>${escapeHtml(preview).slice(0, 160)}</small>
        </button>`;
    })
    .join('');
  root.querySelectorAll('[data-memory-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      const memory = await apiJson(`${API}/memories/${encodeURIComponent(button.dataset.memoryId)}?memory_space_key=${encodeURIComponent(state.selectedMemorySpaceKey || '')}`);
      state.selectedMemory = memory.memory;
      renderJson('memory-detail', memory);
    });
  });
}

function renderWorkspaceList(workspaces) {
  const root = $('workspace-list');
  if (!root) return;
  if (!workspaces.length) {
    root.innerHTML = '<div class="empty">No workspaces found.</div>';
    return;
  }
  root.innerHTML = workspaces
    .map((workspace) => {
      const aliases = Array.isArray(workspace.aliases) ? workspace.aliases.join(', ') : '';
      return `
        <button class="list-item" data-workspace-id="${workspace.workspace_uid}">
          <strong>${escapeHtml(workspace.workspace_uid)}</strong>
          <span>${aliases ? `Aliases: ${escapeHtml(aliases)}` : 'No aliases'}</span>
        </button>`;
    })
    .join('');
  root.querySelectorAll('[data-workspace-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      const uid = button.dataset.workspaceId;
      state.selectedWorkspace = uid;
      const resolved = await apiJson(`${API}/workspaces/${encodeURIComponent(uid)}/resolve?memory_space_key=${encodeURIComponent(state.selectedMemorySpaceKey || '')}`);
      renderJson('workspace-detail', resolved);
    });
  });
}

function renderServiceList(services) {
  const root = $('service-list');
  if (!root) return;
  root.innerHTML = services
    .map(
      (service) => `
        <button class="list-item" data-service-id="${service.service_type}">
          <strong>${escapeHtml(service.service_type)}</strong>
          <span>${service.running ? 'running' : 'stopped'}</span>
          <small>${escapeHtml(service.discovery?.service?.endpoint || service.discovery?.next_step || '')}</small>
        </button>`,
    )
    .join('');
  root.querySelectorAll('[data-service-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      state.selectedService = button.dataset.serviceId;
      const payload = await apiJson(`${API}/services/${encodeURIComponent(state.selectedService)}`);
      renderJson('service-detail', payload);
    });
  });
}

function renderEmbeddingJobs(jobs) {
  const root = $('embedding-jobs');
  if (!root) return;
  if (!jobs.length) {
    root.innerHTML = '<div class="empty">No embedding jobs found.</div>';
    return;
  }
  root.innerHTML = jobs
    .map((job) => {
      const status = job.state || job.status || 'unknown';
      return `
        <button class="list-item" data-embedding-job-id="${escapeHtml(job.id || '')}">
          <strong>${escapeHtml(job.id || 'unknown job')}</strong>
          <span>${escapeHtml(status)} · ${escapeHtml(job.reason || job.error_message || '')}</span>
          <small>${escapeHtml([job.provider, job.model].filter(Boolean).join(' · '))}</small>
        </button>`;
    })
    .join('');
  root.querySelectorAll('[data-embedding-job-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      const jobId = button.dataset.embeddingJobId;
      state.selectedEmbeddingJob = jobId;
      const payload = await apiJson(`${API}/embedding/jobs/${encodeURIComponent(jobId)}?memory_space_key=${encodeURIComponent(state.selectedMemorySpaceKey || '')}`);
      renderJson('embedding-job-detail', payload);
    });
  });
}

function graphLayout(nodes) {
  const groups = ['memory_space', 'workspace', 'type', 'status', 'memory'];
  const positions = new Map();
  groups.forEach((group, index) => {
    const xs = 150 + index * 220;
    const groupNodes = nodes.filter((node) => node.kind === group);
    const step = 560 / Math.max(groupNodes.length + 1, 2);
    groupNodes.forEach((node, nodeIndex) => {
      positions.set(node.id, {
        x: xs,
        y: 80 + step * (nodeIndex + 1),
      });
    });
  });
  return positions;
}

function renderGraph(graph) {
  const svg = $('graph-svg');
  const detail = $('graph-detail');
  if (!svg || !detail) return;
  state.graphData = graph;
  renderJson('graph-detail', graph);
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];
  if (!nodes.length) {
    svg.innerHTML = '<text x="24" y="32" fill="#cbd5e1">No graph nodes match the current filters.</text>';
    return;
  }
  const positions = graphLayout(nodes);
  const nodeRadius = 24;
  const edgeMarkup = edges
    .map((edge) => {
      const source = positions.get(edge.source);
      const target = positions.get(edge.target);
      if (!source || !target) return '';
      return `<line class="edge" x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" />`;
    })
    .join('');
  const nodeMarkup = nodes
    .map((node) => {
      const position = positions.get(node.id) || { x: 80, y: 80 };
      const label = node.label || node.id;
      const classes = ['node', node.kind].join(' ');
      return `
        <g class="${classes}" data-node-id="${escapeHtml(node.id)}" transform="translate(${position.x},${position.y})">
          <circle r="${node.kind === 'memory' ? 28 : nodeRadius}" class="${escapeHtml(node.kind)}"></circle>
          <text class="node-label" text-anchor="middle" y="4">${escapeHtml(label)}</text>
        </g>`;
    })
    .join('');
  svg.innerHTML = `${edgeMarkup}${nodeMarkup}`;
  svg.querySelectorAll('[data-node-id]').forEach((nodeEl) => {
    nodeEl.addEventListener('click', () => {
      const nodeId = nodeEl.dataset.nodeId;
      const node = nodes.find((candidate) => candidate.id === nodeId);
      if (node) {
        renderJson('graph-detail', node);
      }
    });
  });
}

function renderLogSummary(summary) {
  const root = $('log-summary');
  if (root) renderJson('log-summary', summary);
  const tail = $('log-tail');
  if (tail) {
    const recent = summary?.recent;
    if (recent && Array.isArray(recent.lines)) {
      tail.textContent = recent.lines.join('\n');
    } else {
      tail.textContent = 'No log tail available.';
    }
  }
}

function renderDiagnosticsBundle(bundle) {
  state.diagnosticsBundle = bundle;
  renderJson('diagnostics', bundle);
  renderLogSummary(bundle?.logs || null);
}

function renderEmbeddingStatus(payload) {
  renderJson('embedding-status', payload);
  renderJson('embedding-model-state', payload?.model_state || {});
}

function renderDevStatus(payload) {
  renderJson('dev-seed-status', payload);
}

function renderSpaces(spaces) {
  const root = $('memory-spaces');
  if (!root) return;
  root.innerHTML = spaces
    .map(
      (space) => `
        <button class="list-item ${space.selected ? 'selected' : ''}" data-memory-space-key="${space.key}">
          <strong>${escapeHtml(space.key)}${space.is_default ? ' (default)' : ''}</strong>
          <span>${space.exists ? 'database exists' : 'database missing'}</span>
          <small>${escapeHtml(space.db_path)}</small>
        </button>`,
    )
    .join('');
  root.querySelectorAll('[data-memory-space-key]').forEach((button) => {
    button.addEventListener('click', async () => {
      state.selectedMemorySpaceKey = button.dataset.memorySpaceKey;
      $('memory-space-status').textContent = state.selectedMemorySpaceKey;
      await refreshMemories();
      await refreshWorkspaces();
      await refreshConfig();
      showMessage(`Selected memory space: ${state.selectedMemorySpaceKey}`);
    });
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function apiJson(path, options = {}) {
  return await request(path, options);
}

async function refreshContext() {
  const health = await apiJson('/v1/health');
  const status = await apiJson('/v1/status');
  const context = await apiJson(`${API}/context`);
  const memorySpaces = await apiJson(`${API}/memory-spaces`);
  const services = await apiJson(`${API}/services`);
  state.context = context;
  state.selectedMemorySpaceKey = memorySpaces.selected_memory_space_key || context.config.safe_paths.default_memory_space_key;
  $('health-status').textContent = health.status;
  $('service-status').textContent = status.status;
  $('memory-space-status').textContent = state.selectedMemorySpaceKey;
  $('security-warning-text').textContent = context.security.warning;
  renderSpaces(memorySpaces.spaces || []);
  renderServiceList(services.services || []);
  renderJson('config-view', context.config);
  renderJson('diagnostics', context);
  await refreshMemories();
  await refreshWorkspaces();
}

async function refreshMemories() {
  const params = new URLSearchParams();
  const memorySpaceKey = state.selectedMemorySpaceKey || state.context?.config?.safe_paths?.default_memory_space_key;
  if (memorySpaceKey) params.set('memory_space_key', memorySpaceKey);
  const payload = await apiJson(`${API}/memories?${params.toString()}`);
  renderMemoryList(payload.memories || []);
  if (state.selectedMemory) {
    renderJson('memory-detail', { memory: state.selectedMemory });
  }
}

async function refreshWorkspaces() {
  const params = new URLSearchParams();
  const memorySpaceKey = state.selectedMemorySpaceKey || state.context?.config?.safe_paths?.default_memory_space_key;
  if (memorySpaceKey) params.set('memory_space_key', memorySpaceKey);
  const payload = await apiJson(`${API}/workspaces?${params.toString()}`);
  renderWorkspaceList(payload.workspaces || []);
}

async function refreshConfig() {
  const payload = await apiJson(`${API}/config`);
  renderJson('config-view', payload);
}

async function refreshServices() {
  const payload = await apiJson(`${API}/services`);
  renderServiceList(payload.services || []);
}

async function refreshEmbeddingStatus() {
  const payload = await apiJson(
    `${API}/embedding/status?memory_space_key=${encodeURIComponent(state.selectedMemorySpaceKey || '')}`,
  );
  renderEmbeddingStatus(payload);
  return payload;
}

async function refreshEmbeddingJobs() {
  const params = new URLSearchParams();
  if (state.selectedMemorySpaceKey) params.set('memory_space_key', state.selectedMemorySpaceKey);
  const payload = await apiJson(`${API}/embedding/jobs?${params.toString()}`);
  renderEmbeddingJobs(payload.jobs || []);
  return payload;
}

async function refreshDevStatus() {
  const payload = await apiJson(`${API}/dev/status`);
  renderDevStatus(payload);
  return payload;
}

async function refreshDiagnosticsBundle() {
  const payload = await apiJson(
    `${API}/diagnostics?memory_space_key=${encodeURIComponent(state.selectedMemorySpaceKey || '')}&tail_lines=${encodeURIComponent(String(currentTailLines()))}`,
  );
  renderDiagnosticsBundle(payload);
  return payload;
}

async function refreshLogs() {
  const payload = await apiJson(`${API}/logs?tail_lines=${encodeURIComponent(String(currentTailLines()))}`);
  state.logSummary = payload;
  renderLogSummary(payload);
  return payload;
}

async function refreshGraph() {
  const form = $('graph-form');
  const values = form ? formValues(form) : {};
  const params = new URLSearchParams();
  const memorySpaceKey = values.memory_space_key?.trim() || state.selectedMemorySpaceKey || '';
  if (memorySpaceKey) params.set('memory_space_key', memorySpaceKey);
  if (values.space) params.set('space', values.space);
  if (values.workspace_uid) params.set('workspace_uid', values.workspace_uid);
  if (values.type) params.set('type', values.type);
  if (values.status) params.set('status', values.status);
  if (values.include_archived) params.set('include_archived', 'true');
  if (values.limit) params.set('limit', values.limit);
  const payload = await apiJson(`${API}/graph?${params.toString()}`);
  renderGraph(payload);
  return payload;
}

function wireMemoryForms() {
  const searchForm = $('memory-search-form');
  const memoryForm = $('memory-form');
  const listButton = $('memory-list-button');
  const clearButton = $('memory-clear-button');

  listButton?.addEventListener('click', async () => {
    try {
      await refreshMemories();
      showMessage('Memory list refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  clearButton?.addEventListener('click', () => {
    $('memory-results').innerHTML = '';
    $('memory-detail').textContent = 'No memory selected.';
    state.selectedMemory = null;
  });

  searchForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = formValues(searchForm);
    const payload = {
      query: values.query || '',
      scope: values.scope || 'user',
      workspace_uid: values.workspace_uid || null,
      limit: Number(values.limit || 20),
      include_archived: Boolean(values.include_archived),
      type: values.type || null,
      protected_minimum: values.protected_minimum ? Number(values.protected_minimum) : null,
      match_threshold: values.match_threshold ? parseMaybeJson(values.match_threshold) : null,
      memory_space_key: values.memory_space_key || state.selectedMemorySpaceKey || null,
    };
    try {
      const response = await apiJson(`${API}/memories/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      renderMemoryList(response.results || []);
      showMessage(`Search returned ${response.count || 0} memories.`);
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  memoryForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    await submitMemoryForm('add');
  });

  memoryForm?.querySelector('[data-action="update"]')?.addEventListener('click', async () => {
    await submitMemoryForm('update');
  });

  memoryForm?.querySelector('[data-action="archive"]')?.addEventListener('click', async () => {
    await submitMemoryForm('archive');
  });
}

async function submitMemoryForm(action) {
  const form = $('memory-form');
  const values = formValues(form);
  const memoryId = values.memory_id?.trim();
  const basePayload = {
    space: values.space || 'user',
    type: values.type || 'fact',
    content: values.content || '',
    workspace_uid: values.workspace_uid || null,
    metadata: parseMaybeJson(values.metadata),
    source: values.source || null,
    confidence: values.confidence ? Number(values.confidence) : null,
    sensitivity: values.sensitivity || null,
    memory_space_key: values.memory_space_key || state.selectedMemorySpaceKey || null,
  };

  try {
    if (action === 'add') {
      const response = await apiJson(`${API}/memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(basePayload),
      });
      state.selectedMemory = response.memory;
      renderJson('memory-detail', response);
      showMessage('Memory added.');
    } else if (action === 'update') {
      if (!memoryId) throw new Error('Memory ID is required for update.');
      const payload = {
        content: basePayload.content || null,
        type: basePayload.type || null,
        metadata: basePayload.metadata,
        source: basePayload.source,
        confidence: basePayload.confidence,
        sensitivity: basePayload.sensitivity,
        memory_space_key: basePayload.memory_space_key,
      };
      const response = await apiJson(`${API}/memories/${encodeURIComponent(memoryId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      state.selectedMemory = response.memory;
      renderJson('memory-detail', response);
      showMessage('Memory updated.');
    } else if (action === 'archive') {
      if (!memoryId) throw new Error('Memory ID is required for archive.');
      const params = new URLSearchParams();
      if (basePayload.memory_space_key) params.set('memory_space_key', basePayload.memory_space_key);
      const response = await apiJson(`${API}/memories/${encodeURIComponent(memoryId)}/archive?${params.toString()}`, {
        method: 'POST',
      });
      state.selectedMemory = response.memory;
      renderJson('memory-detail', response);
      showMessage('Memory archived.', 'warning');
    }
    await refreshMemories();
  } catch (error) {
    showMessage(error.message, 'error');
  }
}

function wireConfigForms() {
  $('refresh-config')?.addEventListener('click', async () => {
    try {
      await refreshConfig();
      showMessage('Config refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('validate-config')?.addEventListener('click', async () => {
    try {
      const payload = await apiJson(`${API}/config/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      renderJson('config-view', payload);
      showMessage('Config validated.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('config-key-form')?.querySelectorAll('button[data-action]').forEach((button) => {
    button.addEventListener('click', async () => {
      const form = $('config-key-form');
      const values = formValues(form);
      const key = values.key?.trim();
      if (!key) {
        showMessage('Config key is required.', 'error');
        return;
      }
      try {
        if (button.dataset.action === 'get') {
          const payload = await apiJson(`${API}/config/${encodeURIComponent(key)}`);
          renderJson('config-view', payload);
        } else if (button.dataset.action === 'set') {
          const payload = await apiJson(`${API}/config/${encodeURIComponent(key)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: parseMaybeJson(values.value) }),
          });
          renderJson('config-view', payload);
        } else if (button.dataset.action === 'unset') {
          const payload = await apiJson(`${API}/config/${encodeURIComponent(key)}`, {
            method: 'DELETE',
          });
          renderJson('config-view', payload);
        }
        showMessage(`Config ${button.dataset.action} completed.`);
      } catch (error) {
        showMessage(error.message, 'error');
      }
    });
  });
}

function wireWorkspaceForms() {
  $('refresh-workspaces')?.addEventListener('click', async () => {
    try {
      await refreshWorkspaces();
      showMessage('Workspaces refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('workspace-form')?.querySelectorAll('button[data-action]').forEach((button) => {
    button.addEventListener('click', async () => {
      const form = $('workspace-form');
      const values = formValues(form);
      const workspaceUid = values.workspace_uid?.trim();
      const memorySpaceKey = values.memory_space_key?.trim() || state.selectedMemorySpaceKey || null;
      try {
        if (button.dataset.action === 'resolve') {
          if (!workspaceUid) throw new Error('Workspace UID is required.');
          const payload = await apiJson(`${API}/workspaces/${encodeURIComponent(workspaceUid)}/resolve?memory_space_key=${encodeURIComponent(memorySpaceKey || '')}`);
          renderJson('workspace-detail', payload);
        } else if (button.dataset.action === 'rename') {
          if (!workspaceUid) throw new Error('Workspace UID is required.');
          const response = await apiJson(`${API}/workspaces/${encodeURIComponent(workspaceUid)}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_uid: values.new_uid, memory_space_key: memorySpaceKey }),
          });
          renderJson('workspace-detail', response);
          await refreshWorkspaces();
        } else if (button.dataset.action === 'aliases') {
          if (!workspaceUid) throw new Error('Workspace UID is required.');
          const payload = await apiJson(`${API}/workspaces/${encodeURIComponent(workspaceUid)}/aliases?memory_space_key=${encodeURIComponent(memorySpaceKey || '')}`);
          renderJson('workspace-detail', payload);
        } else if (button.dataset.action === 'add-alias') {
          if (!workspaceUid) throw new Error('Workspace UID is required.');
          const response = await apiJson(`${API}/workspaces/${encodeURIComponent(workspaceUid)}/aliases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ alias_uid: values.alias_uid, migrate_existing: Boolean(values.migrate_existing), memory_space_key: memorySpaceKey }),
          });
          renderJson('workspace-detail', response);
          await refreshWorkspaces();
        } else if (button.dataset.action === 'remove-alias') {
          if (!values.alias_uid) throw new Error('Alias UID is required.');
          const payload = await apiJson(`${API}/workspaces/aliases/${encodeURIComponent(values.alias_uid)}?memory_space_key=${encodeURIComponent(memorySpaceKey || '')}`, {
            method: 'DELETE',
          });
          renderJson('workspace-detail', payload);
          await refreshWorkspaces();
        }
        showMessage(`Workspace ${button.dataset.action} completed.`);
      } catch (error) {
        showMessage(error.message, 'error');
      }
    });
  });
}

function wireServiceForms() {
  $('refresh-services')?.addEventListener('click', async () => {
    try {
      await refreshServices();
      showMessage('Services refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('service-form')?.querySelectorAll('button[data-action]').forEach((button) => {
    button.addEventListener('click', async () => {
      const form = $('service-form');
      const values = formValues(form);
      const serviceType = values.service_type || 'api';
      const body = {
        db_path: values.db_path || null,
        log_level: values.log_level || null,
        allow_self_stop: Boolean(values.allow_self_stop),
      };
      try {
        if (button.dataset.action === 'discover') {
          const payload = await apiJson(`${API}/services/${encodeURIComponent(serviceType)}/discover`);
          renderJson('service-detail', payload);
        } else if (button.dataset.action === 'start') {
          const payload = await apiJson(`${API}/services/${encodeURIComponent(serviceType)}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
          renderJson('service-detail', payload);
          await refreshServices();
        } else if (button.dataset.action === 'stop') {
          const payload = await apiJson(`${API}/services/${encodeURIComponent(serviceType)}/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
          renderJson('service-detail', payload);
          await refreshServices();
        } else if (button.dataset.action === 'restart') {
          const payload = await apiJson(`${API}/services/${encodeURIComponent(serviceType)}/restart`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
          renderJson('service-detail', payload);
          await refreshServices();
        }
        showMessage(`Service ${button.dataset.action} completed.`);
      } catch (error) {
        showMessage(error.message, 'error');
      }
    });
  });
}

function wireEmbeddingForms() {
  $('refresh-embedding-status')?.addEventListener('click', async () => {
    try {
      await refreshEmbeddingStatus();
      showMessage('Embedding status refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('refresh-embedding-jobs')?.addEventListener('click', async () => {
    try {
      await refreshEmbeddingJobs();
      showMessage('Embedding jobs refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('run-embedding-maintenance')?.addEventListener('click', async () => {
    try {
      const form = $('embedding-refresh-form');
      const values = form ? formValues(form) : {};
      const payload = await apiJson(ROUTES.embeddingMaintenance, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirm: Boolean(values.confirm),
          memory_space_key: values.memory_space_key || state.selectedMemorySpaceKey || null,
        }),
      });
      renderJson('embedding-job-detail', payload);
      if (payload.status === 'confirmation_required') {
        showMessage(payload.warning || 'Confirmation required.', 'warning');
        return;
      }
      await refreshEmbeddingStatus();
      await refreshEmbeddingJobs();
      showMessage('Embedding maintenance completed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('clear-embedding-jobs')?.addEventListener('click', async () => {
    try {
      const payload = await apiJson(`${API}/embedding/jobs`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ memory_space_key: state.selectedMemorySpaceKey || null }),
      });
      renderJson('embedding-job-detail', payload);
      await refreshEmbeddingJobs();
      showMessage('Embedding job history cleared.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('embedding-refresh-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = formValues(event.currentTarget);
    try {
      const payload = await apiJson(`${API}/embedding/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          space: values.space || null,
          workspace_uid: values.workspace_uid || null,
          include_archived: Boolean(values.include_archived),
          memory_space_key: values.memory_space_key || state.selectedMemorySpaceKey || null,
        }),
      });
      renderJson('embedding-job-detail', payload);
      await refreshEmbeddingStatus();
      await refreshEmbeddingJobs();
      showMessage('Embedding refresh completed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });
}

function wireDevForms() {
  $('refresh-dev-status')?.addEventListener('click', async () => {
    try {
      await refreshDevStatus();
      showMessage('Dev status refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('init-dev-seed')?.addEventListener('click', async () => {
    try {
      const payload = await apiJson(`${API}/dev/seeding/init`, { method: 'POST' });
      renderJson('dev-eval-result', payload);
      await refreshDevStatus();
      showMessage('Seeded dev database initialized.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('reset-dev-seed')?.addEventListener('click', async () => {
    try {
      const payload = await apiJson(`${API}/dev/seeding/reset`, { method: 'POST' });
      renderJson('dev-eval-result', payload);
      await refreshDevStatus();
      showMessage('Seeded dev database reset.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('run-dev-eval')?.addEventListener('click', async () => {
    try {
      const form = $('dev-eval-form');
      const values = form ? formValues(form) : {};
      const payload = await apiJson(`${API}/dev/eval`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: Boolean(values.confirm), memory_space_key: values.memory_space_key || state.selectedMemorySpaceKey || null }) });
      renderJson('dev-eval-result', payload);
      if (payload.status === 'confirmation_required') {
        showMessage(payload.warning || 'Confirmation required.', 'warning');
        return;
      }
      showMessage('Dev eval completed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('threshold-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = formValues(event.currentTarget);
    try {
      const payload = await apiJson(`${API}/dev/optimize-threshold`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start: Number(values.start),
          end: Number(values.end),
          step: Number(values.step),
          beta: Number(values.beta),
          output_format: values.output_format || 'csv',
          output_path: values.output_path || null,
          write_config: Boolean(values.write_config),
          confirm: Boolean(values.confirm),
        }),
      });
      renderJson('threshold-result', payload);
      if (payload.status === 'confirmation_required') {
        showMessage(payload.warning || 'Confirmation required.', 'warning');
        return;
      }
      showMessage('Threshold optimization completed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });
}

function wireGraphForms() {
  $('refresh-graph')?.addEventListener('click', async () => {
    try {
      await refreshGraph();
      showMessage('Graph refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('graph-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      await refreshGraph();
      showMessage('Graph rendered.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });
}

function wireDiagnosticsForms() {
  $('refresh-diagnostics')?.addEventListener('click', async () => {
    try {
      await refreshDiagnosticsBundle();
      showMessage('Diagnostics bundle refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('refresh-logs')?.addEventListener('click', async () => {
    try {
      await refreshLogs();
      showMessage('Logs refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });

  $('copy-diagnostics')?.addEventListener('click', async () => {
    try {
      const text = JSON.stringify(state.diagnosticsBundle || {}, null, 2);
      await navigator.clipboard.writeText(text);
      showMessage('Diagnostics bundle copied.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });
}

function wireRefreshButtons() {
  $('refresh-spaces')?.addEventListener('click', async () => {
    try {
      const payload = await apiJson(`${API}/memory-spaces?memory_space_key=${encodeURIComponent(state.selectedMemorySpaceKey || '')}`);
      renderSpaces(payload.spaces || []);
      showMessage('Memory spaces refreshed.');
    } catch (error) {
      showMessage(error.message, 'error');
    }
  });
}

async function boot() {
  wireTabs();
  wireMemoryForms();
  wireConfigForms();
  wireWorkspaceForms();
  wireServiceForms();
  wireEmbeddingForms();
  wireDevForms();
  wireGraphForms();
  wireDiagnosticsForms();
  wireRefreshButtons();

  try {
    await refreshContext();
    await refreshEmbeddingStatus();
    await refreshEmbeddingJobs();
    await refreshDevStatus();
    await refreshGraph();
    await refreshDiagnosticsBundle();
    await refreshLogs();
    showMessage('WebUI ready.');
  } catch (error) {
    renderText('health-status', 'unavailable');
    renderText('service-status', 'unavailable');
    renderText('memory-space-status', 'unavailable');
    renderJson('diagnostics', { error: String(error) });
    showMessage(error.message, 'error');
  }
}


document.addEventListener('DOMContentLoaded', boot);
