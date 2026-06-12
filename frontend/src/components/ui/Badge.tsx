export function Badge({ children, tone = "neutral" }: { children: string; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  return <span className={["badge", `badge--${tone}`].join(" ")}>{children}</span>;
}
