import { MenuItem } from "../models/MenuItem.js";
import { cosineSimilarity, embed } from "./embeddings.js";

let cache = null; // [{ item, vector }]

/** Build the searchable text for one menu item (what we embed). */
export function itemToText(item) {
  const parts = [
    item.name,
    item.category,
    item.description,
    (item.aliases || []).join(" "),
  ];
  return parts.filter(Boolean).join(" — ");
}

/** Load menu items + their stored embeddings into memory (once). */
export async function loadIndex() {
  if (cache) return cache;
  const items = await MenuItem.find({}).lean();
  const withVec = items.filter((i) => Array.isArray(i.embedding) && i.embedding.length);
  if (withVec.length === 0) {
    throw new Error(
      "No embeddings found. Run: node scripts/buildEmbeddings.js  (after `ollama pull nomic-embed-text`)"
    );
  }
  cache = withVec.map((i) => ({ item: i, vector: i.embedding }));
  return cache;
}

/** Reset the cache (used after re-indexing). */
export function clearIndex() {
  cache = null;
}

/**
 * Retrieve the top-k menu items most relevant to a query string.
 * @returns {Promise<Array<{item, score}>>}
 */
export async function retrieve(query, k = 8) {
  const index = await loadIndex();
  const [qVec] = await embed(query);
  const scored = index.map(({ item, vector }) => ({
    item,
    score: cosineSimilarity(qVec, vector),
  }));
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, k);
}
