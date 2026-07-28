import { MODELS, EXAMPLES } from "@/lib/api";

export default function OrderForm({ text, setText, model, setModel, loading, onSubmit }) {
  return (
    <div className="rounded-2xl border border-counter-line bg-counter-panel/70 p-5 sm:p-6">
      <div className="flex items-center justify-between gap-4">
        <label htmlFor="order" className="text-sm font-medium text-counter-dim">Type an order</label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-counter-dim">Model</span>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="rounded-lg border border-counter-line bg-counter-bg px-2.5 py-1.5 font-mono text-sm text-counter-text focus:border-route-build focus:outline-none"
          >
            {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <input
          id="order"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !loading) onSubmit(); }}
          placeholder="e.g. one cheeseburger, one fries, and a cola"
          className="flex-1 rounded-xl border border-counter-line bg-counter-bg px-4 py-3 text-counter-text placeholder:text-counter-dim/50 focus:border-route-build focus:outline-none focus:ring-2 focus:ring-route-build/20"
        />
        <button
          onClick={onSubmit}
          disabled={loading || !text.trim()}
          className="rounded-xl bg-route-build px-6 py-3 font-medium text-counter-bg transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Sending…" : "Send order"}
        </button>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setText(ex)}
            className="rounded-full border border-counter-line px-3 py-1 text-xs text-counter-dim transition hover:border-route-build/40 hover:text-counter-text"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
