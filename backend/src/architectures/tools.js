import { MenuItem } from "../models/MenuItem.js";

export const toolDefinitions = [
    {
        type: "function",
        function: {
            name: "search_menu",
            description: "Search the menu by a name or keyword. Returns matching items with their itemId, price and availability.",
            parameters: {
                type: "object",
                properties: {
                    query: { type: "string", description: "Item name or keyword, e.g. 'cheeseburger' or 'milkshake'" },
                },
                required: ["query"],
            },
        },
    },
    {
        type: "function",
        function: {
            name: "get_item",
            description: "Get full details of one menu item by its exact itemId, including sizes, options and whether it is available.",
            parameters: {
                type: "object",
                properties: {
                    itemId: { type: "string", description: "Exact menu id, e.g. 'BRG-001'" },
                },
                required: ["itemId"],
            },
        },
    },
    {
        type: "function",
        function: {
            name: "add_item",
            description: "Add a verified item to the order. Only call after confirming the itemId exists and is available.",
            parameters: {
                type: "object",
                properties: {
                    itemId: { type: "string" },
                    quantity: { type: "integer", description: "1 to 10" },
                    modifications: { type: "array", items: { type: "string" }, description: "e.g. ['no onions','large']" },
                },
                required: ["itemId", "quantity"],
            },
        },
    },
];

// Build executors bound to a per-request cart.
export function makeToolExecutors(cart) {
    return {
        async search_menu({ query }) {
            const rx = new RegExp(query.split(/\s+/).join("|"), "i");
            const items = await MenuItem.find({
                $or: [{ name: rx }, { aliases: rx }, { category: rx }],
            }).limit(8).lean();
            return items.map((i) => ({
                itemId: i.itemId, name: i.name, price: i.basePrice, available: i.available,
            }));
        },

        async get_item({ itemId }) {
            const i = await MenuItem.findOne({ itemId: String(itemId).toUpperCase() }).lean();
            if (!i) return { error: `No item with id ${itemId}` };
            return {
                itemId: i.itemId, name: i.name, price: i.basePrice, available: i.available,
                sizes: i.sizes, removableIngredients: i.removableIngredients,
                addons: i.addons, maxQuantityPerOrder: i.maxQuantityPerOrder,
            };
        },

        async add_item({ itemId, quantity = 1, modifications = [] }) {
            const i = await MenuItem.findOne({ itemId: String(itemId).toUpperCase() }).lean();
            if (!i) return { error: `Cannot add: ${itemId} does not exist` };
            if (!i.available) return { error: `Cannot add: ${i.name} is currently unavailable` };
            if (quantity < 1 || quantity > (i.maxQuantityPerOrder || 10)) {
                return { error: `Invalid quantity ${quantity}; max is ${i.maxQuantityPerOrder || 10}` };
            }
            cart.push({ itemId: i.itemId, name: i.name, quantity, modifications });
            return { ok: true, added: { itemId: i.itemId, name: i.name, quantity, modifications } };
        },
    };
}
