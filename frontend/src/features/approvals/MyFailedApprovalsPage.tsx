import { ApprovalsPage } from "./ApprovalsPage";

export function MyFailedApprovalsPage() {
  return <ApprovalsPage status="FAILED" scope="mine" title="My failed approvals" />;
}
