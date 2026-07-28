import { MENU } from "@/lib/menu";

const LABELS = {
  burgers: "Burgers", chicken: "Chicken", sides: "Sides",
  drinks: "Drinks", desserts: "Desserts", meals: "Meals",
};

// Read-only menu shown beside the order box. Clicking an item name drops it into
// the order input so a customer can build an order by tapping.
export default function MenuPanel({ onPick }) {
  return (
    <aside className="rounded-2xl border border-counter-line bg-counter-panel/70 p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-semibold">Menu</h2>
        <span className="font-mono text-xs text-counter-dim">tap to add</span>
      </div>
      <div className="menu-scroll max-h-[70vh] space-y-5 overflow-y-auto pr-1">
        {Object.entries(MENU).map(([cat, items]) => (
          <div key={cat}>
            <h3 className="mb-2 font-mono text-xs uppercase tracking-wider text-route-build/80">
              {LABELS[cat] || cat}
            </h3>
            <ul className="space-y-1">
              {items.map((it) => (
                <li key={it.id}>
                  <button
                    disabled={!it.available}
                    onClick={() => onPick?.(it.name)}
                    className={`flex w-full items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-left text-sm transition
                      ${it.available
                        ? "text-counter-text hover:bg-counter-line/40"
                        : "cursor-not-allowed text-counter-dim/40 line-through"}`}
                  >
                    <span className="truncate">{it.name}</span>
                    {typeof it.price === "number" && (
                      <span className="font-mono text-xs text-counter-dim shrink-0">£{it.price.toFixed(2)}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </aside>
  );
}
