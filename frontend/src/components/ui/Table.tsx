import type { ReactNode } from "react";

export function Table({ children }: { children: ReactNode }) {
  return <table className="table">{children}</table>;
}
