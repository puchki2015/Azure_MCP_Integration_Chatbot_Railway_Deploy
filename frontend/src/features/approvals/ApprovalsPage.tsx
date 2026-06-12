import { useEffect, useState } from "react";
import { Input } from "../../components/ui/Input";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { ApprovalsTable } from "./ApprovalsTable";
import { ApprovalHistoryPanel } from "./ApprovalHistoryPanel";
import { approveApproval, listApprovals, rejectApproval } from "./approvals.api";
import type { ApprovalItem } from "./approvals.types";

type Scope = "mine" | "all";

export function ApprovalsPage({
  status,
  scope = "all",
  title,
  actionable = false
}: {
  status: "PENDING" | "APPROVED" | "REJECTED" | "FAILED";
  scope?: Scope;
  title?: string;
  actionable?: boolean;
}) {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [pendingActionId, setPendingActionId] = useState<number | null>(null);
  const [decisionReasons, setDecisionReasons] = useState<Record<number, string>>({});
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionMessageTone, setActionMessageTone] = useState<"success" | "error" | "info">("info");

  const load = async () => {
    try {
      setLoading(true);
      setItems(await listApprovals(status, scope));
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [status, scope]);

  const refresh = async () => {
    await load();
  };

  const handleAction = async (approvalId: number, action: "approve" | "reject") => {
    try {
      setError(null);
      setActionMessage(null);
      setActionMessageTone("info");
      setPendingActionId(approvalId);

      const reason = decisionReasons[approvalId]?.trim() || undefined;
      if (!reason) {
        throw new Error("Reason is required before approving or rejecting.");
      }

      if (action === "approve") {
        const result = await approveApproval(approvalId, reason);
        if (result.status === "FAILED" || result.error_message) {
          setActionMessageTone("error");
          setActionMessage(
            `${result.message}. Reason: ${result.reason ?? reason}. Error: ${result.error_message ?? "Unknown failure"}`
          );
        } else {
          setActionMessageTone("success");
          setActionMessage(
            `${result.message}. Reason: ${result.reason ?? reason}`
          );
        }
      } else {
        const result = await rejectApproval(approvalId, reason);
        setActionMessageTone("success");
        setActionMessage(
          `${result.message}. Reason: ${result.reason ?? reason}`
        );
      }

      setDecisionReasons((current) => {
        const next = { ...current };
        delete next[approvalId];
        return next;
      });

      await refresh();
    } catch (ex) {
      setActionMessageTone("error");
      setActionMessage(ex instanceof Error ? ex.message : "Failed to update approval");
    } finally {
      setPendingActionId(null);
    }
  };

  if (loading) {
    return (
      <div className="screen-center">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <EmptyState title="Could not load approvals" description={error} />;
  }

  const filteredItems = items.filter((item) => {
    const haystack = [
      item.id,
      item.action,
      item.tool_name,
      item.status,
      item.approved_by,
      item.decision_reason
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return haystack.includes(search.toLowerCase());
  });

  return (
    <div className="approval-page">
      <div className="approval-page__header">
        <div>
          <div className="eyebrow">{title ?? `${scope === "all" ? "Admin" : "My"} approvals`}</div>
          <h1>{status.toLowerCase()} approvals</h1>
        </div>
        <div className="approval-page__toolbar">
          <Input
            value={search}
            placeholder="Search approvals..."
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </div>
      <p className="approval-page__hint">
        A reason is required before approving or rejecting. Approved items stay visible after execution, and failed executions are listed separately.
      </p>
      {actionMessage ? (
        <div className={`error-banner error-banner--${actionMessageTone}`}>{actionMessage}</div>
      ) : null}
      {scope === "all" ? <ApprovalHistoryPanel scope={scope} /> : null}
      {items.length === 0 ? (
        <EmptyState title={`No ${status.toLowerCase()} approvals`} description="Nothing to review right now." />
      ) : filteredItems.length === 0 ? (
        <EmptyState title="No matching approvals" description="Try a different search term." />
      ) : (
        <ApprovalsTable
          items={filteredItems}
          actionable={actionable && status === "PENDING"}
          pendingActionId={pendingActionId}
          decisionReasons={decisionReasons}
          onDecisionReasonChange={(approvalId, value) =>
            setDecisionReasons((current) => ({ ...current, [approvalId]: value }))
          }
          onApprove={(approvalId) => void handleAction(approvalId, "approve")}
          onReject={(approvalId) => void handleAction(approvalId, "reject")}
        />
      )}
    </div>
  );
}
