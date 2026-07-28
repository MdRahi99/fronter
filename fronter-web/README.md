# fronter — order terminal (Next.js frontend)

Single-page demo UI for the Adaptive Hybrid Architecture (D). Type an order or tap
menu items on the right; the app shows whether D built it, asked for a detail, or
refused it, plus the route and response time.

## Run
1. Start your backend on http://localhost:5000 (use the demo router for smooth
   ordering — see the router-demo package).
2. In this folder:
   ```
   npm install
   npm run dev
   ```
3. Open http://localhost:3000

Backend URL is set in `.env.local` (`NEXT_PUBLIC_API_BASE`). If the backend does
not send CORS headers, add this to the Express app once:
```js
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "http://localhost:3000");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});
```

## Notes
- Model dropdown: qwen2.5 (default), llama3, mistral.
- The menu panel is generated from your menu.json. If the menu changes, re-generate
  `src/lib/menu.js` (names + prices + availability), or edit it directly.
- Use exact menu words in orders ("fries", specific burger names) for clean builds.

## Structure
- `src/app/layout.jsx` — root layout, fonts
- `src/app/page.jsx` — two-column page (order flow + menu), state
- `src/lib/api.js` — backend call + route logic + example orders
- `src/lib/menu.js` — menu data for the side panel
- `src/components/OrderForm.jsx` — input, model picker, example chips
- `src/components/MenuPanel.jsx` — tappable menu (right column)
- `src/components/ResultPanel.jsx` — outcome for the chosen route
- `src/components/RouteBadge.jsx` — build / clarify / reject light
- `src/components/Cart.jsx` — validated lines + total
