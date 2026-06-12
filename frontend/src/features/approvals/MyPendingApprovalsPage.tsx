import { ApprovalsPage } from "./ApprovalsPage";

export function MyPendingApprovalsPage() {
  return <ApprovalsPage status="PENDING" scope="mine" title="My approvals" />;
}
