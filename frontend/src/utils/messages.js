export function createMessage(role, content, overrides = {}) {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    status: role === 'assistant' ? 'pending' : 'done',
    createdAt: new Date().toISOString(),
    events: [],
    reactions: [],
    attachments: [],
    ...overrides,
  };
}

export function toChatHistory(messages) {
  return messages
    .filter((message) => ['user', 'assistant', 'system'].includes(message.role))
    .filter((message) => message.content?.trim())
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));
}

export function summarizeJson(data) {
  return JSON.stringify(data, null, 2);
}

export function isSuccessPayload(data) {
  return data?.success !== false;
}
