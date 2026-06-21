async function loadJson(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

function renderText(elementId, value) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = value;
  }
}

function renderPretty(elementId, payload) {
  renderText(elementId, JSON.stringify(payload, null, 2));
}

async function boot() {
  try {
    const [health, status, capabilities] = await Promise.all([
      loadJson('/v1/health'),
      loadJson('/v1/status'),
      loadJson('/v1/capabilities'),
    ]);

    renderText('health-status', health.status);
    renderText('service-status', status.status);
    renderText(
      'security-status',
      `${status.security.authentication} auth, tls=${status.security.tls}`,
    );
    renderPretty('capabilities', capabilities);
    renderPretty('endpoint-snapshot', {
      health: health.endpoints.health,
      status: status.endpoints.status,
      capabilities: capabilities.endpoints.capabilities,
      version: status.version,
      local_first: status.local_first,
    });
  } catch (error) {
    renderText('health-status', 'unavailable');
    renderText('service-status', 'unavailable');
    renderText('security-status', String(error));
    renderText('capabilities', String(error));
    renderText('endpoint-snapshot', String(error));
  }
}

document.addEventListener('DOMContentLoaded', boot);
