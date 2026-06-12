import { ApprovalsPage } from "./ApprovalsPage";
export function PendingApprovalsPage() {
  return <ApprovalsPage status="PENDING" scope="all" title="Admin approvals" actionable />;
}
