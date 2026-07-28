import { ROUTE_META } from "@/lib/api";

const STYLES = {
  build:   "bg-route-build/15 text-route-build ring-route-build/30",
  clarify: "bg-route-clarify/15 text-route-clarify ring-route-clarify/30",
  reject:  "bg-route-reject/15 text-route-reject ring-route-reject/30",
};
const DOT = { build: "bg-route-build", clarify: "bg-route-clarify", reject: "bg-route-reject" };

export default function RouteBadge({ route }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ring-1 ${STYLES[route]}`}>
      <span className={`h-2 w-2 rounded-full ${DOT[route]}`} />
      {ROUTE_META[route].label}
    </span>
  );
}
