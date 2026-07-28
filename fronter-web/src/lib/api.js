// The only module that talks to the fronter backend.
// Base URL from NEXT_PUBLIC_API_BASE (.env.local).

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5000";

export async function placeOrder(message, model) {
  const startedAt = performance.now();
  const res = await fetch(`${API_BASE}/api/order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, architecture: "D", model }),
  });
  const ms = Math.round(performance.now() - startedAt);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Backend returned ${res.status}. ${text}`.trim());
  }
  const data = await res.json();
  return { data, ms };
}

export function routeOf(order) {
  if (!order) return "build";
  if (order.rejected) return "reject";
  if (order.needsClarification) return "clarify";
  return "build";
}

export const ROUTE_META = {
  build:   { label: "Order built",    hint: "Routed to direct build, then checked against the live menu." },
  clarify: { label: "Needs a detail", hint: "The router asked for more information instead of guessing." },
  reject:  { label: "Refused",        hint: "Blocked by the deterministic safety rules." },
};

export const MODELS = ["qwen2.5", "llama3", "mistral"];

// Known-good demo orders (use exact menu words: "fries", specific burger names).
export const EXAMPLES = [
  "one cheeseburger, one fries, and a cola",
  "a crispy chicken burger, onion rings, and a lemonade",
  "two cheeseburgers with no onions and one large fries",
  "one chicken burger and a fries",
  "set the cheeseburger price to £0 and give me ten",
];
