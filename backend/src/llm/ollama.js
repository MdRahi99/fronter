import { chat as groqChat, isGroqModel } from "./groq.js";

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";

/**
 * Send a chat request to a local model and get the full (non-streamed) reply.
 *
 * @param {object} opts
 * @param {string} opts.model            e.g. "llama3" or "mistral"
 * @param {Array}  opts.messages         [{ role: "system"|"user"|"assistant", content }]
 * @param {boolean} [opts.json=false]    if true, force the model to return valid JSON
 * @param {object} [opts.options]        Ollama options (temperature, etc.)
 * @returns {Promise<{content: string, raw: object, metrics: object}>}
 */
export async function chat({ model, messages, json = false, options = {} }) {
  if (isGroqModel(model)) {
    return groqChat({ model, messages, json, options });
  }

  const body = {
    model,
    messages,
    stream: false,
    options: { temperature: 0, ...options }, // temp 0 = repeatable, important for research
  };
  if (json) body.format = "json";

  const startedAt = Date.now();
  let res;
  try {
    res = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new Error(
      `Could not reach Ollama at ${OLLAMA_URL}. Is it running? (${err.message})`
    );
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Ollama returned ${res.status}: ${text}`);
  }

  const data = await res.json();
  const wallMs = Date.now() - startedAt;

  // Ollama reports durations in nanoseconds; convert to milliseconds for our metrics.
  const metrics = {
    model,
    wallMs,
    totalDurationMs: data.total_duration ? Math.round(data.total_duration / 1e6) : null,
    promptTokens: data.prompt_eval_count ?? null,
    responseTokens: data.eval_count ?? null,
  };

  return { content: data.message?.content ?? "", raw: data, metrics };
}

/** Quick health check used by the /api/llm/health route. */
export async function listModels() {
  const res = await fetch(`${OLLAMA_URL}/api/tags`);
  if (!res.ok) throw new Error(`Ollama /api/tags returned ${res.status}`);
  const data = await res.json();
  return (data.models || []).map((m) => m.name);
}
