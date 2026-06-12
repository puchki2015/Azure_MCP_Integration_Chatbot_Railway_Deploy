import { ApprovalsPage } from "./ApprovalsPage";

export function MyRejectedApprovalsPage() {
  return <ApprovalsPage status="REJECTED" scope="mine" title="My rejected approvals" />;
}
