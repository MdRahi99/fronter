// VERSION B — Retrieval-Augmented Generation (RAG)
// Instead of putting the WHOLE menu in the prompt (Version A), we embed the
// customer's order, retrieve only the most relevant menu items, and put just
// those in the prompt. Smaller prompt, focused context.

import { chat } from "../llm/ollama.js";
import { retrieve } from "../rag/vectorStore.js";

function buildMenuText(retrieved) {
  return retrieved
    .map(({ item }) => {
      const price = `£${item.basePrice.toFixed(2)}`;
      const avail = item.available ? "" : " (UNAVAILABLE)";
      return `${item.itemId} | ${item.name} | ${item.category} | ${price}${avail}`;
    })
    .join("\n");
}

const SYSTEM_PROMPT = `You are an order-taking assistant for a fast-food restaurant called fronter.
You will be given a SHORTLIST of relevant menu items and a customer message.
Return ONLY a JSON object with this exact shape:
{
  "items": [
    { "itemId": "<menu id>", "name": "<menu name>", "quantity": <number>, "modifications": ["<text>"] }
  ],
  "reply": "<a short friendly sentence to the customer>",
  "needsClarification": <true|false>
}
Rules:
- Only use itemId values that appear in the shortlist. Never invent items or prices.
- If the needed item is not in the shortlist, set needsClarification to true and say so in reply.
- If the order is clear, set needsClarification to false.`;

export async function versionB({ customerMessage, model = "llama3", k = 8 }) {
  const retrieved = await retrieve(customerMessage, k);
  const menuText = buildMenuText(retrieved);

  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: `RELEVANT MENU ITEMS:\n${menuText}\n\nCUSTOMER: ${customerMessage}` },
  ];

  const { content, metrics } = await chat({ model, messages, json: true });

  let order;
  try {
    order = JSON.parse(content);
  } catch {
    order = { items: [], reply: "Sorry, I couldn't understand that order.", needsClarification: true, parseError: true };
  }

  return {
    architecture: "B",
    model,
    order,
    metrics,
    retrieved: retrieved.map((r) => ({ itemId: r.item.itemId, score: Number(r.score.toFixed(3)) })),
  };
}
