export default function Cart({ items }) {
  if (!items?.length) return <p className="text-counter-dim">No items were added.</p>;
  const total = items.reduce((s, it) => s + (it.price || 0) * (it.quantity || 1), 0);
  return (
    <div className="divide-y divide-counter-line">
      {items.map((it, i) => (
        <div key={i} className="flex items-start justify-between py-3">
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-counter-dim text-sm">{it.quantity || 1}×</span>
              <span className="font-medium truncate">{it.name || it.itemId}</span>
            </div>
            {it.modifications?.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1.5">
                {it.modifications.map((m, k) => (
                  <span key={k} className="rounded bg-counter-line/60 px-2 py-0.5 text-xs text-counter-dim">{m}</span>
                ))}
              </div>
            )}
            <div className="mt-1 font-mono text-xs text-counter-dim/70">{it.itemId}</div>
          </div>
          {typeof it.price === "number" && (
            <span className="font-mono text-counter-text shrink-0 pl-4">
              £{(it.price * (it.quantity || 1)).toFixed(2)}
            </span>
          )}
        </div>
      ))}
      <div className="flex items-center justify-between pt-3">
        <span className="text-counter-dim">Total</span>
        <span className="font-mono text-lg font-semibold text-route-build">£{total.toFixed(2)}</span>
      </div>
    </div>
  );
}
