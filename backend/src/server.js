import cors from "cors";
import "dotenv/config";
import express from "express";
import { connectDB } from "./db.js";
import menuRoutes from "./routes/menu.js";
import orderRoutes from "./routes/order.js";

const app = express();
app.use(cors());
app.use(express.json());

app.get("/api/health", (req, res) => {
  res.json({ status: "ok", service: "Fronter-backend", time: new Date().toISOString() });
});

app.use("/api/menu", menuRoutes);
app.use("/api/llm", orderRoutes);   // /api/llm/health
app.use("/api", orderRoutes);       // /api/order

// Express 5: async errors are forwarded automatically; this catches them all
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: "Internal server error" });
});

const PORT = process.env.PORT || 5000;

connectDB()
  .then(() => {
    app.listen(PORT, () => console.log(`Fronter backend running on http://localhost:${PORT}`));
  })
  .catch((err) => {
    console.error("Failed to start:", err.message);
    process.exit(1);
  });
