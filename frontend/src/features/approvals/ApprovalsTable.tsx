import { Table } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ApprovalStatusBadge } from "./ApprovalStatusBadge";
import type { ApprovalItem } from "./approvals.types";
import { formatDate } from "../../utils/formatDate";

export function ApprovalsTable({
  items,
  onApprove,
  onReject,
  actionable = false,
  pendingActionId = null,
  decisionReasons = {},
  onDecisionReasonChange
}: {
  items: ApprovalItem[];
  onApprove?: (approvalId: number) => void;
  onReject?: (approvalId: number) => void;
  actionable?: boolean;
  pendingActionId?: number | null;
  decisionReasons?: Record<number, string>;
  onDecisionReasonChange?: (approvalId: number, value: string) => void;
}) {
  return (
    <Table>
      <thead>
        <tr>
          <th>ID</th>
          <th>User</th>
          <th>Action</th>
          <th>Tool</th>
          <th>Status</th>
          <th>Reason</th>
          <th>Created</th>
          {actionable ? <th>Actions</th> : null}
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>{item.id}</td>
            <td>
              <div>{item.user_email ?? "N/A"}</div>
              <small className="session-summary-card__meta">
                {item.user_id ? `User ID ${item.user_id}` : ""}
              </small>
            </td>
            <td>{item.action}</td>
            <td>{item.tool_name ?? "N/A"}</td>
            <td><ApprovalStatusBadge status={item.status} /></td>
            <td>
              {actionable && item.status === "PENDING" ? (
                <Input
                  className="approval-reason-input"
                  value={decisionReasons?.[item.id] ?? ""}
                  placeholder="Decision reason (required)"
                  aria-label={`Decision reason for approval ${item.id}`}
                  onChange={(event) => onDecisionReasonChange?.(item.id, event.target.value)}
                />
              ) : (
                <div className="approval-reason-cell">
                  {item.decision_reason ? (
                    <div>Reason: {item.decision_reason}</div>
                  ) : null}
                  {item.error_message ? (
                    <div className="approval-error-text">Error: {item.error_message}</div>
                  ) : null}
                  {!item.decision_reason && !item.error_message ? "-" : null}
                </div>
              )}
            </td>
            <td>{formatDate(item.created_at)}</td>
            {actionable ? (
              <td>
                <div className="approval-actions">
                  <Button
                    variant="secondary"
                    disabled={pendingActionId === item.id || !decisionReasons?.[item.id]?.trim()}
                    onClick={() => onApprove?.(item.id)}
                  >
                    {pendingActionId === item.id ? "Working..." : "Approve"}
                  </Button>
                  <Button
                    variant="ghost"
                    disabled={pendingActionId === item.id || !decisionReasons?.[item.id]?.trim()}
                    onClick={() => onReject?.(item.id)}
                  >
                    Reject
                  </Button>
                </div>
              </td>
            ) : null}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
