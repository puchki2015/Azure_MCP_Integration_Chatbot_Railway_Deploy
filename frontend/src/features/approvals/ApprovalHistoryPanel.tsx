import { useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { formatDate } from "../../utils/formatDate";
import { ApprovalActionDrawer } from "./ApprovalActionDrawer";
import { listApprovalActionHistory } from "./approvalHistory.api";
import type { ApprovalActionLogItem } from "./approvalHistory.api";

export function ApprovalHistoryPanel({ scope = "all" }: { scope?: "mine" | "all" }) {
  const [items, setItems] = useState<ApprovalActionLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<ApprovalActionLogItem | null>(null);

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      try {
        const data = await listApprovalActionHistory(scope, 8);
        if (mounted) {
          setItems(data);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      mounted = false;
    };
  }, [scope]);

  return (
    <>
      <Card className="approval-history-panel">
        <div className="eyebrow">Action history</div>
        <h2>Recent admin actions</h2>
        {loading ? (
          <div className="screen-center screen-center--compact">
            <Spinner />
          </div>
        ) : items.length === 0 ? (
          <p className="approval-history-panel__empty">No recent approval actions.</p>
        ) : (
          <div className="approval-history-panel__list">
            {items.map((item) => (
              <div key={item.id} className="approval-history-panel__item">
                <div className="approval-history-panel__item-header">
                  <strong>Approval {item.approval_id}</strong>
                  <Button variant="ghost" onClick={() => setSelectedItem(item)}>
                    View details
                  </Button>
                </div>
                <span>
                  {item.action} · {item.status}
                </span>
                <small>{item.admin_email}</small>
                <small>{formatDate(item.created_at)}</small>
                {item.error_message ? <small className="approval-error-text">{item.error_message}</small> : null}
                {item.reason ? <small>Reason: {item.reason}</small> : null}
              </div>
            ))}
          </div>
        )}
      </Card>
      <ApprovalActionDrawer item={selectedItem} onClose={() => setSelectedItem(null)} />
    </>
  );
}
