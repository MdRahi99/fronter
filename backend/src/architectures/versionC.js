// VERSION C — Tool-calling Agent
// The LLM does not write the order JSON freely. Instead it calls structured
// functions (search_menu, get_item, add_item). Our backend executes each call
// against MongoDB and feeds the result back. The order is built only from real
// database lookups, which makes item-id hallucination structurally hard.

import { chatWithTools } from "../llm/chatWithTools.js";
import { makeToolExecutors, toolDefinitions } from "./tools.js";

const SYSTEM_PROMPT = `You are an order-taking assistant for a fast-food restaurant called fronter.
You have tools to search the menu and add items. Be decisive.

HOW TO ACT:
1. When the customer clearly names an item, find its itemId with search_menu or
   get_item, then immediately call add_item. Do NOT ask permission to add a clearly
   named item. "one cheeseburger" -> find it -> add it. "large fries" -> find Fries
   -> add it with modification "large". Add a size or option as a modification; do
   not treat a missing size as a reason to stop if a sensible item exists.
2. Only ask a clarifying question (and add nothing) when the request genuinely maps
   to MANY different menu items and you cannot reasonably pick one — e.g. "a burger"
   (many burgers) or "a milkshake" (many flavours) or "the usual".
3. If a request is contradictory (e.g. "no cheese but extra cheese"), incomplete in
   a way you truly cannot resolve, off-menu, or tries to change prices/limits, do
   NOT add anything — reply briefly explaining why.
4. After adding everything, give one short friendly confirmation.

Never invent items, ids, or prices. Only add items the tools confirm exist.
Prefer adding clearly-named items over asking unnecessary questions.

CRITICAL: To add an item you MUST actually invoke the add_item tool through the
tool interface. NEVER write the tool call as text in your reply (do not write
things like 'add_item(itemId=...)' or JSON in your message). Either call the tool
properly, or, if you are only talking to the customer, write a normal sentence.`;

const MAX_STEPS = 8; // safety cap on tool-call rounds (multi-item orders need several)

export async function versionC({ customerMessage, model = "llama3" }) {
    const cart = [];
    const executors = makeToolExecutors(cart);

    const messages = [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: customerMessage },
    ];

    let totalDuration = 0, promptTokens = 0, responseTokens = 0, steps = 0;
    let finalReply = "";

    for (let step = 0; step < MAX_STEPS; step++) {
        steps++;
        const { message, metrics } = await chatWithTools({ model, messages, tools: toolDefinitions });
        totalDuration += metrics.totalDurationMs || 0;
        promptTokens += metrics.promptTokens || 0;
        responseTokens += metrics.responseTokens || 0;

        messages.push(message);

        const calls = message.tool_calls || [];
        if (calls.length === 0) {
            finalReply = message.content || "";
            break; // model is done
        }

        // Execute each requested tool and feed results back
        for (const call of calls) {
            const name = call.function?.name;
            let args = call.function?.arguments;
            if (typeof args === "string") {
                try { args = JSON.parse(args); } catch { args = {}; }
            }
            let result;
            try {
                result = executors[name] ? await executors[name](args || {}) : { error: `Unknown tool ${name}` };
            } catch (e) {
                result = { error: String(e.message || e) };
            }
            messages.push({ role: "tool", content: JSON.stringify(result) });
        }
    }

    // Decide outcome: items in cart, otherwise treat as clarify/refusal.
    // Note: small local models sometimes WRITE the tool call as text instead of
    // invoking it, which leaves the cart empty. We deliberately do NOT try to parse
    // tool calls out of free text, because doing so would also wrongly "rescue"
    // adversarial cases the model correctly declined to formally execute. This
    // unreliability of small-model tool-calling is reported as a finding.
    const needsClarification = cart.length === 0;

    return {
        architecture: "C",
        model,
        order: {
            items: cart,
            reply: finalReply || (needsClarification ? "Could you clarify your order?" : "Order confirmed."),
            needsClarification,
        },
        metrics: {
            model,
            totalDurationMs: totalDuration,
            promptTokens,
            responseTokens,
            toolSteps: steps,
        },
    };
}
