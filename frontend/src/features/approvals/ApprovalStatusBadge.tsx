import { Badge } from "../../components/ui/Badge";

export function ApprovalStatusBadge({ status }: { status: string }) {
  const tone =
    status === "APPROVED" ? "success" :
    status === "REJECTED" ? "danger" :
    status === "EXECUTED" ? "info" :
    status === "FAILED" ? "danger" :
    "warning";

  return <Badge tone={tone}>{status}</Badge>;
}
