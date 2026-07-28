"use client";

import MenuPanel from "@/components/MenuPanel";
import OrderForm from "@/components/OrderForm";
import ResultPanel from "@/components/ResultPanel";
import { MODELS, placeOrder } from "@/lib/api";
import { useState } from "react";

export default function Page() {
  const [text, setText] = useState("");
  const [model, setModel] = useState(MODELS[0]); // qwen2.5
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit() {
    const message = text.trim();
    if (!message || loading) return;
    setLoading(true);
    setError("");
    try {
      const res = await placeOrder(message, model);
      setResult(res);
    } catch (e) {
      setError(e.message || "Could not reach the backend. Is it running on port 5000?");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  // Tapping a menu item appends it to the current order text.
  function addToOrder(name) {
    setText((t) => {
      const trimmed = t.trim();
      if (!trimmed) return `one ${name.toLowerCase()}`;
      return `${trimmed}, one ${name.toLowerCase()}`;
    });
  }

  return (
    <main className="relative z-10 mx-auto max-w-6xl px-5 py-10 sm:py-14">
      <header className="mb-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-route-build font-mono text-lg font-bold text-counter-bg">f</div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Fronter</h1>
            <p className="font-mono text-xs text-counter-dim">order terminal · adaptive hybrid (D)</p>
          </div>
        </div>
        <p className="mt-4 max-w-xl text-sm leading-relaxed text-counter-dim">
          Type any order, or tap items from the menu. The hybrid architecture decides whether to
          build it, ask for a missing detail, or refuse it — then checks every item against the live menu.
        </p>
      </header>

      {/* two columns: order flow (left, wider) + menu (right) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <OrderForm
            text={text} setText={setText}
            model={model} setModel={setModel}
            loading={loading} onSubmit={handleSubmit}
          />

          {error && (
            <div className="mt-5 rounded-xl border border-route-reject/30 bg-route-reject/10 p-4 text-sm text-route-reject">
              {error}
            </div>
          )}

          {loading && (
            <div className="mt-5 flex items-center gap-3 rounded-2xl border border-counter-line bg-counter-panel/40 p-5 text-counter-dim">
              <span className="h-2 w-2 rounded-full bg-route-build animate-pulse2" />
              Routing the order…
            </div>
          )}

          {result && !loading && <div className="mt-5"><ResultPanel result={result} /></div>}

          {!result && !loading && !error && (
            <div className="mt-5 rounded-2xl border border-dashed border-counter-line/70 p-8 text-center text-sm text-counter-dim">
              Your order result will appear here.
            </div>
          )}
        </div>

        <MenuPanel onPick={addToOrder} />
      </div>
    </main>
  );
}
