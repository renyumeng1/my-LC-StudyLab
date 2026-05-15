const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function readJson(response) {
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || data.error || response.statusText);
  }
  return data;
}

async function jsonRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });
  return readJson(response);
}

export async function getChatModes() {
  return jsonRequest('/chat/modes');
}

export async function sendChat(request) {
  return jsonRequest('/chat/', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function streamChat(request, handlers) {
  const controller = new AbortController();
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...request, streaming: true }),
    signal: controller.signal,
  });

  if (!response.ok || !response.body) {
    const data = await readJson(response);
    throw new Error(data.detail || data.error || 'Stream request failed');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  async function pump() {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';
      for (const rawEvent of events) {
        const line = rawEvent.split('\n').find((item) => item.startsWith('data: '));
        if (!line) continue;
        const payload = JSON.parse(line.slice(6));
        handlers.onEvent?.(payload);
        if (payload.type === 'chunk') handlers.onChunk?.(payload.content || '');
        if (payload.type === 'error') handlers.onError?.(payload.message || payload.error || 'Stream error');
        if (payload.type === 'end') handlers.onEnd?.(payload);
      }
    }
  }

  const completed = pump();
  return { abort: () => controller.abort(), completed };
}

export async function getSupportedExtensions() {
  return jsonRequest('/rag/supported-extensions');
}

export async function listIndexes() {
  return jsonRequest('/rag/indexes');
}

export async function createIndex(request) {
  return jsonRequest('/rag/indexes', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function updateIndex(name, request) {
  return jsonRequest(`/rag/indexes/${encodeURIComponent(name)}/documents`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function deleteIndex(name) {
  return jsonRequest(`/rag/indexes/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
}

export async function queryRag(request) {
  return jsonRequest('/rag/query', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function startWorkflow(request) {
  return jsonRequest('/workflow/start', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function submitWorkflowAnswers(threadId, answers) {
  return jsonRequest(`/workflow/${encodeURIComponent(threadId)}/answers`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  });
}

export async function getWorkflowState(threadId) {
  return jsonRequest(`/workflow/${encodeURIComponent(threadId)}/state`);
}

export async function getWorkflowHistory(threadId) {
  return jsonRequest(`/workflow/${encodeURIComponent(threadId)}/history`);
}
