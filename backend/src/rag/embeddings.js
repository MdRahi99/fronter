const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";
const EMBED_MODEL = process.env.EMBED_MODEL || "nomic-embed-text";

/**
 * Embed one or many strings.
 * @param {string|string[]} input
 * @returns {Promise<number[][]>} array of vectors (one per input string)
 */
export async function embed(input) {
  const inputs = Array.isArray(input) ? input : [input];
  const res = await fetch(`${OLLAMA_URL}/api/embed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: EMBED_MODEL, input: inputs }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Ollama /api/embed returned ${res.status}: ${text}`);
  }
  const data = await res.json();
  return data.embeddings; // array of vectors
}

/** Cosine similarity. Ollama vectors are unit-length, so this is a dot product. */
export function cosineSimilarity(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot;
}
