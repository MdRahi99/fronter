import { routeOf, ROUTE_META } from "@/lib/api";
import RouteBadge from "./RouteBadge";
import Cart from "./Cart";

export default function ResultPanel({ result }) {
  const { data, ms } = result;
  const order = data.order || {};
  const route = routeOf(order);
  return (
    <div className="animate-rise rounded-2xl border border-counter-line bg-counter-panel/70 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <RouteBadge route={route} />
        <div className="flex items-center gap-3 font-mono text-xs text-counter-dim">
          <span>{data.model || "—"}</span>
          <span className="text-counter-line">|</span>
          <span>{ms} ms</span>
        </div>
      </div>
      <p className="mt-3 text-sm text-counter-dim">{ROUTE_META[route].hint}</p>
      {order.reply && (
        <p className="mt-4 border-l-2 border-counter-line pl-3 text-counter-text/90">{order.reply}</p>
      )}
      <div className="mt-5">
        {route === "build" && <Cart items={order.items} />}
        {route === "clarify" && (
          <div className="rounded-xl bg-route-clarify/10 p-4 text-route-clarify">
            The order needs one more detail before it can be built.
          </div>
        )}
        {route === "reject" && (
          <div className="rounded-xl bg-route-reject/10 p-4 text-route-reject">
            This request was refused by the safety rules and never reached the menu.
          </div>
        )}
      </div>
    </div>
  );
}
