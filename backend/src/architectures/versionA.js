import { chat } from "../llm/ollama.js";
import { MenuItem } from "../models/MenuItem.js";

function buildMenuText(items) {
  // A compact, readable menu the model can reason over.
  return items
    .map((i) => {
      const price = `£${i.basePrice.toFixed(2)}`;
      const avail = i.available ? "" : " (UNAVAILABLE)";
      return `${i.itemId} | ${i.name} | ${i.category} | ${price}${avail}`;
    })
    .join("\n");
}

const SYSTEM_PROMPT = `You are an order-taking assistant for a fast-food restaurant called fronter.
You will be given the full menu and a customer message.
Return ONLY a JSON object describing the order, with this exact shape:
{
  "items": [
    { "itemId": "<menu id>", "name": "<menu name>", "quantity": <number>, "modifications": ["<text>"] }
  ],
  "reply": "<a short friendly sentence to the customer>",
  "needsClarification": <true|false>
}
Rules:
- Only use itemId values that appear in the menu. Never invent items or prices.
- If the customer asks for something not on the menu, set needsClarification to true and explain in reply.
- If the order is clear, set needsClarification to false.`;

export async function versionA({ customerMessage, model = "llama3" }) {
  const items = await MenuItem.find({}).lean();
  const menuText = buildMenuText(items);

  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: `MENU:\n${menuText}\n\nCUSTOMER: ${customerMessage}` },
  ];

  const { content, metrics } = await chat({ model, messages, json: true });

  let order;
  try {
    order = JSON.parse(content);
  } catch {
    order = { items: [], reply: "Sorry, I couldn't understand that order.", needsClarification: true, parseError: true };
  }

  return {
    architecture: "A",
    model,
    order,
    metrics,
  };
}
