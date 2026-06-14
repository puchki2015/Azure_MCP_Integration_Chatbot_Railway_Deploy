import { Navigate, Route, Routes } from "react-router-dom";
import { PublicLayout } from "./app/layouts/PublicLayout";
import { ChatLayout } from "./app/layouts/ChatLayout";
import { AdminLayout } from "./app/layouts/AdminLayout";
import { RequireAuth } from "./features/auth/RequireAuth";
import { RequireAdmin } from "./features/auth/RequireAdmin";
import { LoginPage } from "./features/auth/LoginPage";
import { AuthCallbackPage } from "./features/auth/AuthCallbackPage";
import { ChatPage } from "./features/chat/ChatPage";
import { AzureResourceCostsPage } from "./features/chat/AzureResourceCostsPage";
import { PromoVideoPage } from "./features/promo/PromoVideoPage";
import { PendingApprovalsPage } from "./features/approvals/PendingApprovalsPage";
import { ApprovedApprovalsPage } from "./features/approvals/ApprovedApprovalsPage";
import { FailedApprovalsPage } from "./features/approvals/FailedApprovalsPage";
import { RejectedApprovalsPage } from "./features/approvals/RejectedApprovalsPage";
import { MyPendingApprovalsPage } from "./features/approvals/MyPendingApprovalsPage";
import { MyApprovedApprovalsPage } from "./features/approvals/MyApprovedApprovalsPage";
import { MyFailedApprovalsPage } from "./features/approvals/MyFailedApprovalsPage";
import { MyRejectedApprovalsPage } from "./features/approvals/MyRejectedApprovalsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/demo" element={<PromoVideoPage />} />
      </Route>

      <Route
        element={
          <RequireAuth>
            <ChatLayout />
          </RequireAuth>
        }
      >
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:sessionId" element={<ChatPage />} />
        <Route path="/costs" element={<AzureResourceCostsPage />} />
        <Route path="/approvals" element={<Navigate to="/approvals/pending" replace />} />
        <Route path="/approvals/pending" element={<MyPendingApprovalsPage />} />
        <Route path="/approvals/approved" element={<MyApprovedApprovalsPage />} />
        <Route path="/approvals/failed" element={<MyFailedApprovalsPage />} />
        <Route path="/approvals/rejected" element={<MyRejectedApprovalsPage />} />
      </Route>

      <Route
        element={
          <RequireAdmin>
            <AdminLayout />
          </RequireAdmin>
        }
      >
        <Route path="/admin" element={<Navigate to="/admin/pending" replace />} />
        <Route path="/admin/pending" element={<PendingApprovalsPage />} />
        <Route path="/admin/approved" element={<ApprovedApprovalsPage />} />
        <Route path="/admin/failed" element={<FailedApprovalsPage />} />
        <Route path="/admin/rejected" element={<RejectedApprovalsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
