import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../app/providers/AuthProvider";
import { isRealEntraConfigured } from "../../services/msal";

type ThemeName = "dark" | "black" | "white" | "matrix" | "sunset";

const themeLabels: Record<ThemeName, string> = {
  dark: "Dark Blue",
  black: "Pure Black",
  white: "Arctic White",
  matrix: "Emerald Matrix",
  sunset: "Sunset Purple",
};

const themeParticles: Record<ThemeName, { primary: string; accent: string }> = {
  dark: { primary: "#0078D4", accent: "#7C3AED" },
  black: { primary: "#00D4FF", accent: "#FF2D55" },
  white: { primary: "#0078D4", accent: "#5C2D91" },
  matrix: { primary: "#00FF41", accent: "#00CC33" },
  sunset: { primary: "#FF6B35", accent: "#C026D3" },
};

function buildParticles(theme: ThemeName) {
  const { primary, accent } = themeParticles[theme];
  return Array.from({ length: 18 }, (_, index) => ({
    key: `${theme}-${index}`,
    size: 2 + ((index * 7) % 4),
    left: (index * 17) % 100,
    duration: 10 + ((index * 3) % 16),
    delay: (index * 5) % 12,
    color: index % 2 === 0 ? primary : accent,
  }));
}

const sections = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how" },
  { label: "Integrations", href: "#integrations" },
  { label: "Pricing", href: "#pricing" },
];

export function LoginPage() {
  const navigate = useNavigate();
  const { login, status } = useAuth();
  const [loginError, setLoginError] = useState<string | null>(null);
  const [theme, setTheme] = useState<ThemeName>("dark");

  const particles = useMemo(() => buildParticles(theme), [theme]);

  useEffect(() => {
    if (status === "authenticated") {
      navigate("/chat", { replace: true });
    }
  }, [navigate, status]);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("azureops-theme") as ThemeName | null;
    if (savedTheme && savedTheme in themeLabels) {
      setTheme(savedTheme);
    }
  }, []);

  useEffect(() => {
    const previousTheme = document.body.getAttribute("data-theme");
    document.body.setAttribute("data-theme", theme);
    window.localStorage.setItem("azureops-theme", theme);

    return () => {
      if (previousTheme) {
        document.body.setAttribute("data-theme", previousTheme);
      } else {
        document.body.removeAttribute("data-theme");
      }
    };
  }, [theme]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.12 }
    );

    document.querySelectorAll(".landing-reveal").forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  const signIn = async () => {
    try {
      setLoginError(null);
      await login();
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Microsoft sign-in failed");
    }
  };

  const ctaLabel = isRealEntraConfigured ? "Sign in with Microsoft" : "Enable Microsoft sign-in";

  return (
    <div className="landing-page" id="top">
      <div className="landing-page__mesh" />
      <div className="landing-page__particles" aria-hidden="true">
        {particles.map((particle) => (
          <span
            key={particle.key}
            className="landing-page__particle"
            style={{
              width: `${particle.size}px`,
              height: `${particle.size}px`,
              left: `${particle.left}%`,
              animationDuration: `${particle.duration}s`,
              animationDelay: `${particle.delay}s`,
              background: `radial-gradient(circle, ${particle.color}99, transparent)`,
            }}
          />
        ))}
      </div>

      <div className="landing-theme-switcher" aria-label="Theme switcher">
        {(["dark", "black", "white", "matrix", "sunset"] as ThemeName[]).map((name) => (
          <button
            key={name}
            type="button"
            className={`landing-theme-switcher__btn${theme === name ? " active" : ""}`}
            data-theme-name={name}
            title={themeLabels[name]}
            aria-label={themeLabels[name]}
            onClick={() => setTheme(name)}
          >
            <span className="landing-theme-switcher__tooltip">{themeLabels[name]}</span>
          </button>
        ))}
      </div>

      <nav className="landing-nav landing-reveal">
        <Link className="landing-nav__brand" to="/">
          <span className="landing-nav__orb">AI</span>
          AzureOPS<span className="landing-nav__accent">AI</span>
        </Link>
        <ul className="landing-nav__links">
          {sections.map((section) => (
            <li key={section.label}>
              <a href={section.href}>{section.label}</a>
            </li>
          ))}
        </ul>
        <button type="button" className="landing-nav__cta" onClick={signIn} disabled={status === "loading" || !isRealEntraConfigured}>
          {ctaLabel}
        </button>
      </nav>

      <section className="landing-hero">
        <div className="landing-hero__badge landing-reveal">
          <span className="landing-hero__badgeDot" />
          Now in public beta - Azure AI OPS v2.0
        </div>
        <h1 className="landing-reveal">
          Ask anything about
          <br />
          your <span className="landing-hero__grad">Azure Cloud</span>
          <br />
          in plain language
        </h1>
        <p className="landing-hero__sub landing-reveal">
          Azure AI Ops connects directly to your subscriptions and lets you query, diagnose,
          and manage resources through natural conversation - no CLI, no portal hunting.
        </p>
        <div className="landing-hero__actions landing-reveal">
          <button type="button" className="landing-btn landing-btn--primary" onClick={signIn} disabled={status === "loading" || !isRealEntraConfigured}>
            {ctaLabel}
          </button>
          <Link className="landing-btn landing-btn--ghost" to="/demo">
            Watch 2-min demo -&gt;
          </Link>
        </div>
        {loginError ? <p className="landing-warning landing-reveal">{loginError}</p> : null}
        {!isRealEntraConfigured ? (
          <p className="landing-warning landing-reveal">
            Microsoft sign-in is not configured yet. Set `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_TENANT_ID`, and `VITE_ENTRA_API_SCOPE` in `frontend/.env`.
          </p>
        ) : null}

        <div className="landing-chat-demo landing-reveal" aria-label="Azure AI Ops chat preview">
          <div className="landing-chat-window">
            <div className="landing-chat-window__topbar">
              <span className="landing-dot landing-dot--red" />
              <span className="landing-dot landing-dot--yellow" />
              <span className="landing-dot landing-dot--green" />
              <span className="landing-chat-window__title">AzureOPS AI - prod-subscription</span>
            </div>
            <div className="landing-chat-window__body">
              <div className="landing-msg landing-msg--user">
                <div className="landing-avatar landing-avatar--user">U</div>
                <div className="landing-bubble landing-bubble--user">Which VMs in eastus are running over 85% CPU?</div>
              </div>
              <div className="landing-msg">
                <div className="landing-avatar landing-avatar--ai">AI</div>
                <div className="landing-bubble landing-bubble--ai">
                  Found <strong>3 VMs</strong> in <code>eastus</code> above 85% CPU right now:
                  <br />
                  <br />
                  <strong>vm-api-prod-02</strong> - 97.3% - Standard_D4s_v3
                  <br />
                  <strong>vm-worker-06</strong> - 91.1% - Standard_D2s_v3
                  <br />
                  <strong>vm-batch-01</strong> - 86.4% - Standard_B4ms
                  <br />
                  <br />
                  Want me to scale out the <code>vm-api-prod</code> scale set or create an alert rule?
                </div>
              </div>
              <div className="landing-msg landing-msg--user">
                <div className="landing-avatar landing-avatar--user">U</div>
                <div className="landing-bubble landing-bubble--user">Scale out the api set by 2 instances</div>
              </div>
              <div className="landing-msg">
                <div className="landing-avatar landing-avatar--ai">AI</div>
                <div className="landing-bubble landing-bubble--ai">
                  Scaling <code>vm-api-prod-scaleset</code> from 4 -&gt; 6 instances...
                  <br />
                  <span className="landing-success">Done in 47s.</span> New instances are healthy and receiving traffic.
                </div>
              </div>
            </div>
            <div className="landing-chat-window__inputbar">
              <input className="landing-chat-input" placeholder="Ask about your Azure resources..." readOnly />
              <button type="button" className="landing-chat-send">
                Send -&gt;
              </button>
            </div>
          </div>
        </div>
      </section>

      <div className="landing-stats-strip landing-reveal">
        <div className="landing-stat">
          <div className="landing-stat__num">200+</div>
          <div className="landing-stat__label">Azure resource types supported</div>
        </div>
        <div className="landing-stat">
          <div className="landing-stat__num">&lt;2s</div>
          <div className="landing-stat__label">Avg. query response time</div>
        </div>
        <div className="landing-stat">
          <div className="landing-stat__num">50k+</div>
          <div className="landing-stat__label">Teams using AzureOPS AI</div>
        </div>
        <div className="landing-stat">
          <div className="landing-stat__num">99.9%</div>
          <div className="landing-stat__label">Platform uptime SLA</div>
        </div>
      </div>

      <section className="landing-section" id="features">
        <div className="landing-reveal">
          <div className="landing-eyebrow">// Capabilities</div>
          <h2 className="landing-section__title">Your cloud, conversationally</h2>
          <p className="landing-section__sub">
            From cost investigation to incident response, Azure AI Ops turns complex cloud operations into simple questions.
          </p>
        </div>
        <div className="landing-features-grid">
          <article className="landing-feature-card landing-reveal">
            <div className="landing-feature-card__icon landing-feature-card__icon--blue">🔍</div>
            <h3>Natural language queries</h3>
            <p>Ask "which storage accounts have public access enabled?" and get an instant, actionable answer - no Kusto required.</p>
          </article>
          <article className="landing-feature-card landing-reveal">
            <div className="landing-feature-card__icon landing-feature-card__icon--purple">⚙️</div>
            <h3>Conversational resource management</h3>
            <p>Scale, restart, tag, and configure resources directly from chat. Every action is logged and reversible.</p>
          </article>
          <article className="landing-feature-card landing-reveal">
            <div className="landing-feature-card__icon landing-feature-card__icon--green">💰</div>
            <h3>Cost intelligence</h3>
            <p>"Why did my bill spike this month?" Get a breakdown by service, region, and tag - with optimization recommendations.</p>
          </article>
          <article className="landing-feature-card landing-reveal">
            <div className="landing-feature-card__icon landing-feature-card__icon--amber">🚨</div>
            <h3>Incident & alert triage</h3>
            <p>Surface firing alerts, correlate logs, and suggest root cause hypotheses - all in one conversational thread.</p>
          </article>
          <article className="landing-feature-card landing-reveal">
            <div className="landing-feature-card__icon landing-feature-card__icon--red">🛡️</div>
            <h3>Security posture review</h3>
            <p>Ask "what's exposed to the internet?" and receive a prioritized list of misconfigurations with remediation steps.</p>
          </article>
          <article className="landing-feature-card landing-reveal">
            <div className="landing-feature-card__icon landing-feature-card__icon--teal">🤖</div>
            <h3>Automated runbooks</h3>
            <p>Turn repeated multi-step operations into saved prompts your whole team can invoke with a single command.</p>
          </article>
        </div>
      </section>

      <section className="landing-section landing-section--how" id="how">
        <div className="landing-how-grid">
          <div className="landing-reveal">
            <div className="landing-eyebrow">// How it works</div>
            <h2 className="landing-section__title">
              Connected to Azure.
              <br />
              Talking to you.
            </h2>
            <p className="landing-section__sub landing-section__sub--spaced">
              Azure AI Ops reads your live resource graph, metrics, and logs - then translates your plain-English intent into safe, audited actions.
            </p>
            <div className="landing-steps">
              <div className="landing-step">
                <div className="landing-step__num">01</div>
                <div className="landing-step__text">
                  <h4>Connect your subscription</h4>
                  <p>Grant read (+ optional write) access in two clicks. No agents, no VPNs - Azure RBAC handles permissions.</p>
                </div>
              </div>
              <div className="landing-step">
                <div className="landing-step__num">02</div>
                <div className="landing-step__text">
                  <h4>Ask in plain English</h4>
                  <p>Type questions just like you'd ask a colleague. Our AI understands Azure context, jargon, and relationships.</p>
                </div>
              </div>
              <div className="landing-step">
                <div className="landing-step__num">03</div>
                <div className="landing-step__text">
                  <h4>Review, approve, act</h4>
                  <p>Any write action shows a diff preview before executing. Every operation is logged to your audit trail.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="landing-terminal landing-reveal">
            <div className="landing-terminal__bar">
              <span className="landing-dot landing-dot--red" />
              <span className="landing-dot landing-dot--yellow" />
              <span className="landing-dot landing-dot--green" />
              <span>azureops - eastus . prod</span>
            </div>
            <div className="landing-terminal__body">
              <div>
                <span className="landing-terminal__prompt">you</span> <span className="landing-terminal__cmd"> -&gt; </span>
                <span className="landing-terminal__out">Show my top 5 cost drivers this month</span>
              </div>
              <div className="landing-terminal__muted">Querying Cost Management API...</div>
              <br />
              <div>
                <span className="landing-terminal__warn">💡 Top 5 services . Jun 2026</span>
              </div>
              <div>
                <span className="landing-terminal__val">1.</span> <span className="landing-terminal__out">Virtual Machines</span> <span className="landing-terminal__val">$4,821</span>
              </div>
              <div>
                <span className="landing-terminal__val">2.</span> <span className="landing-terminal__out">Azure SQL</span> <span className="landing-terminal__val">$1,203</span>
              </div>
              <div>
                <span className="landing-terminal__val">3.</span> <span className="landing-terminal__out">Blob Storage</span> <span className="landing-terminal__val">$847</span>
              </div>
              <div>
                <span className="landing-terminal__val">4.</span> <span className="landing-terminal__out">App Service</span> <span className="landing-terminal__val">$514</span>
              </div>
              <div>
                <span className="landing-terminal__val">5.</span> <span className="landing-terminal__out">Azure Kubernetes</span> <span className="landing-terminal__val">$389</span>
              </div>
              <br />
              <div className="landing-terminal__muted">VMs up 23% vs last month - 4 dev VMs running 24/7.</div>
              <div className="landing-terminal__muted">Recommend auto-shutdown policy.</div>
              <br />
              <div>
                <span className="landing-terminal__prompt">you</span> <span className="landing-terminal__cmd"> -&gt; </span>
                <span className="landing-terminal__muted">enable auto-shutdown on dev VMs</span>
                <span className="landing-terminal__cursor">▌</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section landing-section--integrations landing-reveal" id="integrations">
        <div className="landing-eyebrow">// Integrations</div>
        <h2 className="landing-section__title">Plugs into your stack</h2>
        <p className="landing-section__sub landing-section__sub--center">
          Azure AI Ops connects with your monitoring, alerting, and collaboration tools to keep context in one place.
        </p>
        <div className="landing-logos-row">
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">☁️</span>Azure Monitor</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🔷</span>Azure Resource Graph</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">📊</span>Log Analytics</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🔔</span>Azure Alerts</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">💬</span>Microsoft Teams</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🟣</span>Slack</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🔧</span>Azure DevOps</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">📡</span>Grafana</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🐙</span>GitHub Actions</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🎯</span>PagerDuty</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🗃️</span>ServiceNow</div>
          <div className="landing-logo-pill"><span className="landing-logo-pill__icon">🔐</span>Entra ID</div>
        </div>
      </section>

      <section className="landing-cta landing-reveal" id="pricing">
        <div className="landing-cta__card">
          <h2>Start talking to your cloud today</h2>
          <p>Free for up to 2 subscriptions - No credit card required - SOC 2 Type II certified</p>
          <div className="landing-cta__row">
            <input className="landing-cta__email" type="email" placeholder="you@company.com" />
            <button type="button" className="landing-btn landing-btn--primary landing-cta__button" onClick={signIn} disabled={status === "loading" || !isRealEntraConfigured}>
              {ctaLabel}
            </button>
          </div>
          <p className="landing-cta__footnote">Trusted by engineering teams at Contoso, Fabrikam, Northwind & 50,000+ others</p>
        </div>
      </section>

      <footer className="landing-footer landing-reveal">
        <div className="landing-footer__logo">
          AzureOPS<span className="landing-footer__accent">AI</span>
        </div>
        <div className="landing-footer__links">
          <a href="#">Docs</a>
          <a href="#">Blog</a>
          <a href="#">Privacy</a>
          <a href="#">Terms</a>
          <a href="#">Status</a>
        </div>
        <div className="landing-footer__copy">© 2026 AzureOPS AI. All rights reserved.</div>
      </footer>
    </div>
  );
}
