// chatWithTools.js — tool-calling variant of the Ollama client (for Version C).
// Sends the menu-interaction tools, lets the model call them, executes each call
// against MongoDB, and feeds results back until the model stops calling tools.

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";

export async function chatWithTools({ model, messages, tools }) {
    const body = {
        model,
        messages,
        tools,
        stream: false,
        options: { temperature: 0 },
    };
    const res = await fetch(`${OLLAMA_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Ollama /api/chat (tools) returned ${res.status}: ${text}`);
    }
    const data = await res.json();
    return {
        message: data.message,
        metrics: {
            model,
            totalDurationMs: data.total_duration ? Math.round(data.total_duration / 1e6) : null,
            promptTokens: data.prompt_eval_count ?? null,
            responseTokens: data.eval_count ?? null,
        },
    };
}
