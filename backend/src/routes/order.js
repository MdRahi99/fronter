import { Router } from "express";
import { versionA } from "../architectures/versionA.js";
import { versionB } from "../architectures/versionB.js";
import { versionC } from "../architectures/versionC.js";
import { versionD } from "../architectures/versionD.js";
import { listModels } from "../llm/ollama.js";

const router = Router();

// GET /api/llm/health -> confirms backend can see Ollama and lists models
router.get("/health", async (req, res) => {
  try {
    const models = await listModels();
    res.json({ ollama: "reachable", models });
  } catch (err) {
    res.status(502).json({ ollama: "unreachable", error: err.message });
  }
});

// POST /api/order  body: { message: "two cheeseburgers", architecture: "A", model: "llama3" }
router.post("/order", async (req, res, next) => {
  try {
    const { message, architecture = "A", model = "llama3" } = req.body;
    if (!message || typeof message !== "string") {
      return res.status(400).json({ error: "Body must include a 'message' string." });
    }

    let result;
    switch (architecture.toUpperCase()) {
      case "A":
        result = await versionA({ customerMessage: message, model });
        break;
      case "B":
        result = await versionB({ customerMessage: message, model });
        break;
      case "C":
        result = await versionC({ customerMessage: message, model });
        break;
      case "D":
        result = await versionD({ customerMessage: message, model });
        break;
      default:
        return res.status(400).json({ error: `Architecture '${architecture}' not built yet.` });
    }

    res.json(result);
  } catch (err) {
    next(err);
  }
});

export default router;
