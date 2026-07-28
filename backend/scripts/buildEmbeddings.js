// buildEmbeddings.js — compute an embedding for every menu item and save it
// back onto the MenuItem document in MongoDB. Run ONCE (re-run if the menu changes).
//
//   ollama pull nomic-embed-text      # one time
//   node scripts/buildEmbeddings.js

import "dotenv/config";
import { connectDB, disconnectDB } from "../src/db.js";
import { MenuItem } from "../src/models/MenuItem.js";
import { embed } from "../src/rag/embeddings.js";
import { itemToText } from "../src/rag/vectorStore.js";

async function run() {
  await connectDB();
  const items = await MenuItem.find({});
  console.log(`Embedding ${items.length} menu items with nomic-embed-text...`);

  const texts = items.map(itemToText);
  const vectors = await embed(texts); // batch: one call for all items

  if (vectors.length !== items.length) {
    throw new Error(`Got ${vectors.length} vectors for ${items.length} items`);
  }

  for (let i = 0; i < items.length; i++) {
    items[i].embedding = vectors[i];
    await items[i].save();
  }

  console.log(`Saved embeddings (dim=${vectors[0].length}) to all items.`);
  await disconnectDB();
  console.log("Done. Version B is ready to use.");
}

run().catch((err) => {
  console.error("Embedding build failed:", err.message);
  process.exit(1);
});
