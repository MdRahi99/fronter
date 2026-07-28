import { MenuItem } from "../models/MenuItem.js";

export async function validateCart(cart) {
    const validItems = [];
    const problems = [];

    for (const line of cart || []) {
        const rawId = (line.itemId || "").toString().toUpperCase();
        const qty = Number(line.quantity || 0);

        // 1) exists?
        const item = await MenuItem.findOne({ itemId: rawId }).lean();
        if (!item) {
            problems.push({
                itemId: rawId, issue: "not_found",
                detail: `Item ${rawId || "(blank)"} does not exist on the menu.`
            });
            continue;
        }

        // 2) available?
        if (!item.available) {
            problems.push({
                itemId: rawId, issue: "unavailable",
                detail: `${item.name} is currently unavailable.`
            });
            continue;
        }

        // 3) quantity sane and within the per-item limit?
        const maxQ = item.maxQuantityPerOrder || 10;
        if (!Number.isFinite(qty) || qty < 1) {
            problems.push({
                itemId: rawId, issue: "bad_quantity",
                detail: `Invalid quantity for ${item.name}.`
            });
            continue;
        }
        if (qty > maxQ) {
            problems.push({
                itemId: rawId, issue: "over_limit",
                detail: `${item.name}: quantity ${qty} exceeds the maximum of ${maxQ}.`
            });
            continue;
        }

        // 4) price tampering? If the line carries a price, it MUST match the menu.
        if (line.price !== undefined && line.price !== null) {
            const claimed = Number(line.price);
            if (!Number.isFinite(claimed) || Math.abs(claimed - item.basePrice) > 0.001) {
                problems.push({
                    itemId: rawId, issue: "price_mismatch",
                    detail: `${item.name}: price must be ${item.basePrice}, not ${line.price}.`
                });
                continue;
            }
        }

        // passed every check -> keep it, with the AUTHORITATIVE price from the DB
        validItems.push({
            itemId: item.itemId,
            name: item.name,
            quantity: qty,
            modifications: Array.isArray(line.modifications) ? line.modifications : [],
            price: item.basePrice,            // always the real price, never the model's
        });
    }

    return {
        valid: problems.length === 0,
        validItems,
        problems,
    };
}
