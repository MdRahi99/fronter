import { Router } from "express";
import { MenuItem } from "../models/MenuItem.js";

const router = Router();

// GET /api/menu            -> all items (optionally ?category=burgers&available=true)
router.get("/", async (req, res) => {
  const filter = {};
  if (req.query.category) filter.category = req.query.category;
  if (req.query.available !== undefined) filter.available = req.query.available === "true";
  const items = await MenuItem.find(filter).sort({ category: 1, itemId: 1 }).lean();
  res.json({ count: items.length, items });
});

// GET /api/menu/:itemId    -> one item by its itemId (e.g. BRG-001)
router.get("/:itemId", async (req, res) => {
  const item = await MenuItem.findOne({ itemId: req.params.itemId.toUpperCase() }).lean();
  if (!item) return res.status(404).json({ error: `Item ${req.params.itemId} not found` });
  res.json(item);
});

export default router;
