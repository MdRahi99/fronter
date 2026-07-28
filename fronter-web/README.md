# Fronter — order terminal (Next.js frontend)

Single-page demo UI for the Adaptive Hybrid Architecture (D). Type an order or tap
menu items on the right; the app shows whether D built it, asked for a detail, or
refused it, plus the route and response time.

## Run

1. Start your backend on http://localhost:5000
2. In this folder:
   ```
   npm install
   npm run dev
   ```
3. Open http://localhost:3000

Backend URL is set in `.env.local` (`NEXT_PUBLIC_API_BASE`).

## Notes

- Model dropdown: qwen2.5 (default), llama3, mistral.
- The menu panel is generated from your menu.json. If the menu changes, re-generate
  `src/lib/menu.js` (names + prices + availability), or edit it directly.
- Use exact menu words in orders ("fries", specific burger names) for clean builds.
