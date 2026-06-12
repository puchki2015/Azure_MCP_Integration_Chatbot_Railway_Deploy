import { useEffect } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { useAuth } from "../../app/providers/AuthProvider";
import { isRealEntraConfigured } from "../../services/msal";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, status, user } = useAuth();
  const [loginError, setLoginError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") {
      navigate("/chat", { replace: true });
    }
  }, [navigate, status]);

  return (
    <div className="landing">
      <div className="landing__glow landing__glow--one" />
      <div className="landing__glow landing__glow--two" />
      <section className="landing__hero card">
        <div className="eyebrow">Azure AI Ops</div>
        <h1>Operate Azure through a guided, modern chat workspace.</h1>
        <p className="landing__lead">
          Sign in with Microsoft Entra ID to start a new chat session, review approvals, and keep everything organized in one place.
        </p>
        <div className="landing__cta-row">
          <Button
            onClick={async () => {
              try {
                setLoginError(null);
                await login();
              } catch (error) {
                setLoginError(error instanceof Error ? error.message : "Microsoft sign-in failed");
              }
            }}
            disabled={status === "loading" || !isRealEntraConfigured}
          >
            {isRealEntraConfigured ? "Sign in with Microsoft" : "Enable Microsoft sign-in"}
          </Button>
          <span className="landing__hint">Secure sign-in with Entra ID</span>
        </div>
        {!isRealEntraConfigured ? (
          <p className="landing__warning">
            Microsoft sign-in is not configured yet. Set `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_TENANT_ID`, and `VITE_ENTRA_API_SCOPE` in `frontend/.env`.
          </p>
        ) : null}
        {loginError ? <p className="landing__warning">{loginError}</p> : null}

        <div className="landing__stats">
          <div>
            <strong>Chat</strong>
            <span>Session-based operations</span>
          </div>
          <div>
            <strong>Approvals</strong>
            <span>Pending, approved, rejected</span>
          </div>
          <div>
            <strong>Admin</strong>
            <span>Visibility into workflow state</span>
          </div>
        </div>
      </section>

      <aside className="landing__panel card">
        <div className="landing__panelHeader">
          <div className="landing__avatar">AI</div>
          <div>
            <h2>Workspace overview</h2>
            <p>{user ? `Welcome back, ${user.displayName}` : "A focused interface for Azure operations."}</p>
          </div>
        </div>

        <div className="landing__featureList">
          <div className="landing__feature">
            <span className="landing__featureDot" />
            <div>
              <strong>Session-first chat</strong>
              <p>New sessions are created automatically after login.</p>
            </div>
          </div>
          <div className="landing__feature">
            <span className="landing__featureDot" />
            <div>
              <strong>Approval aware</strong>
              <p>Mutating actions flow into admin review when required.</p>
            </div>
          </div>
          <div className="landing__feature">
            <span className="landing__featureDot" />
            <div>
              <strong>Right-side history</strong>
              <p>Switch between sessions from a clean sidebar panel.</p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
