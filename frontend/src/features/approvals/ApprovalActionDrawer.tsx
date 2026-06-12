import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { formatDate } from "../../utils/formatDate";
import type { ApprovalActionLogItem } from "./approvalHistory.api";

function prettyJson(value: unknown) {
  if (value == null) {
    return "-";
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ApprovalActionDrawer({
  item,
  onClose
}: {
  item: ApprovalActionLogItem | null;
  onClose: () => void;
}) {
  if (!item) {
    return null;
  }

  return (
    <div className="approval-drawer">
      <Card className="approval-drawer__panel">
        <div className="approval-drawer__header">
          <div>
            <div className="eyebrow">Action details</div>
            <h3>Approval {item.approval_id}</h3>
          </div>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </div>

        <div className="approval-drawer__grid">
          <div><strong>Status</strong><span>{item.status}</span></div>
          <div><strong>Action</strong><span>{item.action}</span></div>
          <div><strong>Admin</strong><span>{item.admin_email}</span></div>
          <div><strong>Session</strong><span>{item.session_id ?? "-"}</span></div>
          <div><strong>Tool</strong><span>{item.tool_name ?? "-"}</span></div>
          <div><strong>Created</strong><span>{formatDate(item.created_at)}</span></div>
        </div>

        {item.reason ? (
          <section className="approval-drawer__section">
            <strong>Reason</strong>
            <pre>{item.reason}</pre>
          </section>
        ) : null}

        <section className="approval-drawer__section">
          <strong>Payload</strong>
          <pre>{prettyJson(item.payload)}</pre>
        </section>

        <section className="approval-drawer__section">
          <strong>Execution result</strong>
          <pre>{item.result_text ?? item.error_message ?? "-"}</pre>
        </section>

        {item.error_message ? (
          <section className="approval-drawer__section">
            <strong>Error</strong>
            <pre className="approval-error-text">{item.error_message}</pre>
          </section>
        ) : null}
      </Card>
    </div>
  );
}
