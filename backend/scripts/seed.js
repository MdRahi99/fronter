import "dotenv/config";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { connectDB, disconnectDB } from "../src/db.js";
import { MenuItem } from "../src/models/MenuItem.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MENU_PATH = path.resolve(__dirname, "../../data/menu.json");

async function validateReferences(items) {
  const ids = new Set(items.map((i) => i.itemId));
  const problems = [];
  for (const item of items) {
    for (const comp of item.components ?? []) {
      if (comp.default && !ids.has(comp.default)) {
        problems.push(`${item.itemId}: component default ${comp.default} does not exist`);
      }
      for (const swap of comp.allowedSwaps ?? []) {
        if (!ids.has(swap.itemId)) {
          problems.push(`${item.itemId}: swap ${swap.itemId} does not exist`);
        }
      }
    }
  }
  return problems;
}

async function seed() {
  const raw = await readFile(MENU_PATH, "utf8");
  const data = JSON.parse(raw);
  const items = data.items;

  console.log(`Loaded ${items.length} items from menu.json (schema v${data.schemaVersion})`);

  const problems = await validateReferences(items);
  if (problems.length) {
    console.error("Reference problems found — fix menu.json first:");
    problems.forEach((p) => console.error(" -", p));
    process.exit(1);
  }
  console.log("Reference integrity check passed.");

  await connectDB();
  await MenuItem.deleteMany({});
  await MenuItem.insertMany(items);

  const count = await MenuItem.countDocuments();
  console.log(`Seeded ${count} menu items into '${MenuItem.collection.name}' collection.`);

  await disconnectDB();
  console.log("Done.");
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
