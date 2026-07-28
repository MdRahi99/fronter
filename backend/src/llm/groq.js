const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";

// Map the short --model names you pass on the CLI to real Groq model IDs.
// Add more here if you want to try other hosted models later.
const GROQ_MODEL_MAP = {
  groq: "llama-3.3-70b-versatile",
  "groq-70b": "llama-3.3-70b-versatile",
  "llama-3.3-70b": "llama-3.3-70b-versatile",
  "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
};

/** True when this model name should be routed to Groq instead of Ollama. */
export function isGroqModel(model) {
  return typeof model === "string" && (model in GROQ_MODEL_MAP || model.startsWith("groq"));
}

function resolveGroqModel(model) {
  return GROQ_MODEL_MAP[model] || "llama-3.3-70b-versatile";
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function chat({ model, messages, json = false, options = {} }) {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    throw new Error("GROQ_API_KEY is not set. Add it to backend/.env");
  }

  const body = {
    model: resolveGroqModel(model),
    messages,
    stream: false,
    temperature: options.temperature ?? 0, // temp 0 = repeatable, same as Ollama runs
  };
  if (options.max_tokens) body.max_completion_tokens = options.max_tokens;
  if (json) body.response_format = { type: "json_object" }; // OpenAI-style JSON mode

  const maxAttempts = 5;
  const startedAt = Date.now();

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    let res;
    try {
      res = await fetch(GROQ_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify(body),
      });
    } catch (err) {
      throw new Error(`Could not reach Groq API. (${err.message})`);
    }

    // Rate limited or transient server error -> wait and retry.
    if (res.status === 429 || res.status >= 500) {
      if (attempt === maxAttempts) {
        const text = await res.text();
        throw new Error(`Groq returned ${res.status} after ${maxAttempts} tries: ${text}`);
      }
      // Respect Retry-After header if present, else exponential backoff.
      const retryAfter = parseFloat(res.headers.get("retry-after"));
      const waitMs = Number.isFinite(retryAfter) ? retryAfter * 1000 : attempt * 8000;
      await sleep(waitMs);
      continue;
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Groq returned ${res.status}: ${text}`);
    }

    const data = await res.json();
    const wallMs = Date.now() - startedAt;

    // Groq gives token usage and timing (in seconds) under usage / x_groq.
    const usage = data.usage || {};
    const totalTimeS =
      usage.total_time ??
      (((usage.prompt_time || 0) + (usage.completion_time || 0)) || null);

    const metrics = {
      model: body.model,
      wallMs,
      totalDurationMs: totalTimeS ? Math.round(totalTimeS * 1000) : wallMs,
      promptTokens: usage.prompt_tokens ?? null,
      responseTokens: usage.completion_tokens ?? null,
    };

    return { content: data.choices?.[0]?.message?.content ?? "", raw: data, metrics };
  }

  // Unreachable, but keeps the linter happy.
  throw new Error("Groq request failed unexpectedly.");
}
