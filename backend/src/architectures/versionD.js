// VERSION D -- Adaptive Hybrid Architecture (the contribution).
//
// Pipeline:
//   customer text
//     -> router (Python: safety rules + ML classifier) decides:
//          reject  -> refuse politely (no LLM call needed)
//          clarify -> ask a question (no cart built)
//          execute -> build the cart with a fast direct-prompt builder
//     -> validator (Node: checks cart vs MongoDB menu) cleans the result
//     -> return final order + metrics
//
// DESIGN RATIONALE (dissertation):
//   D does not invent a new ordering method. It ROUTES each order to the approach
//   that handles it best (direct build for clear orders, clarify for unclear,
//   reject for attacks), then VALIDATES every result against the menu. This gives
//   A/B-level accuracy on simple orders WITHOUT their hallucination risk, plus
//   C-level caution on hard orders, in one architecture.

import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import { chat } from "../llm/ollama.js";
import { MenuItem } from "../models/MenuItem.js";
import { validateCart } from "./validator.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// ml/ folder is at <project>/ml ; backend is at <project>/backend
const ML_DIR = path.resolve(__dirname, "..", "..", "..", "ml");
const PYTHON = process.env.PYTHON_BIN || "python";

// ---- call the Python router (rules + classifier) for a routing decision ----
function getRoute(text) {
    return new Promise((resolve) => {
        const proc = spawn(PYTHON, ["router_cli.py", text], { cwd: ML_DIR });
        let out = "", err = "";
        proc.stdout.on("data", d => out += d);
        proc.stderr.on("data", d => err += d);
        proc.on("close", () => {
            try { resolve(JSON.parse(out.trim())); }
            catch { resolve({ route: "clarify", reason: "router_error", type: null, confidence: null, _err: err.trim() }); }
        });
    });
}

// ---- fast direct-prompt builder for the EXECUTE path ----
// Reached only for orders the router judged simple/complex (clear, answerable).
async function buildCartDirect(text, model) {
    const menu = await MenuItem.find({ available: true })
        .select("itemId name basePrice -_id").lean();
    const menuList = menu.map(m => `${m.itemId} = ${m.name} (£${m.basePrice})`).join("\n");

    const system =
        `You are an order builder for the fast-food restaurant "fronter".
Use ONLY these menu items (use the exact itemId):
${menuList}

Return STRICT JSON only, no prose:
{"items":[{"itemId":"BRG-001","quantity":1,"modifications":["no onions"]}]}
Rules: use real itemIds from the list; quantity is an integer; modifications is a
list of short strings (sizes, add/remove). Do not invent items or prices.`;

    const res = await chat({
        model,
        messages: [{ role: "system", content: system }, { role: "user", content: text }],
        options: { temperature: 0 },
    });

    let items = [];
    try {
        const raw = (res.content || "").replace(/```json|```/g, "").trim();
        const start = raw.indexOf("{"), end = raw.lastIndexOf("}");
        const parsed = JSON.parse(raw.slice(start, end + 1));
        if (Array.isArray(parsed.items)) items = parsed.items;
    } catch { items = []; }

    return { items, metrics: res.metrics || {} };
}

export async function versionD({ customerMessage, model = "llama3" }) {
    const t0 = Date.now();

    // --- Step 1: route ---
    const decision = await getRoute(customerMessage);

    // --- Step 2: act on the route ---
    if (decision.route === "reject") {
        return finalize("D", model, [], decision,
            "I can't help with that request.", false, t0, {}, [], true);
    }

    if (decision.route === "clarify") {
        return finalize("D", model, [], decision,
            "Could you clarify exactly what you'd like to order?", true, t0, {});
    }

    // route === "execute": build then validate
    const built = await buildCartDirect(customerMessage, model);
    const { validItems, problems, valid } = await validateCart(built.items);

    const needsClarification = validItems.length === 0;
    let reply;
    if (validItems.length === 0) {
        reply = "I couldn't confirm any valid items — could you clarify your order?";
    } else if (problems.length > 0) {
        reply = "Order confirmed (some items couldn't be added).";
    } else {
        reply = "Order confirmed.";
    }

    return finalize("D", model, validItems, decision, reply, needsClarification, t0,
        built.metrics, problems);
}

function finalize(arch, model, items, decision, reply, needsClarification, t0, metrics, problems = [], rejected = false) {
    return {
        architecture: arch,
        model,
        order: { items, reply, needsClarification, rejected },
        routing: {                       // exposed for analysis/transparency
            route: decision.route,
            reason: decision.reason,
            predictedType: decision.type,
            confidence: decision.confidence,
        },
        validation: { problems },
        metrics: {
            model,
            totalDurationMs: Date.now() - t0,
            promptTokens: metrics.promptTokens ?? null,
            responseTokens: metrics.responseTokens ?? null,
        },
    };
}
