import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

type Scene = {
  kicker: string;
  title: string;
  text: string;
  bullets: string[];
  accent: string;
  terminal: string[];
};

const scenes: Scene[] = [
  {
    kicker: "Opening",
    title: "Talk to your Azure cloud",
    text: "Meet Azure OPS AI, a premium assistant for cloud operations, built for plain-English control.",
    bullets: ["Mesh gradients", "Soft glow", "Product-led motion"],
    accent: "from-cyan-400/30 to-blue-500/20",
    terminal: [
      "> Azure OPS AI",
      "> Conversational cloud operations",
      "> Secure, polished, and auditable"
    ]
  },
  {
    kicker: "Problem",
    title: "Too many tools. Too much context.",
    text: "Portal tabs, alerts, dashboards, and logs compete for attention while operators chase the answer.",
    bullets: ["Cluttered workflows", "Context switching", "Slower decisions"],
    accent: "from-sky-400/25 to-indigo-500/20",
    terminal: [
      "portal / metrics / alerts / logs",
      "one answer spread across many screens"
    ]
  },
  {
    kicker: "Chat",
    title: "Ask in plain English",
    text: "Azure OPS AI turns simple questions into immediate answers with a calm, conversational interface.",
    bullets: ["Type a question", "See the answer", "Stay in flow"],
    accent: "from-violet-400/25 to-blue-500/20",
    terminal: [
      "Which VMs in eastus are above 85% CPU?",
      "Found 3 VMs with elevated load",
      "vm-api-prod-02 · 97.3%"
    ]
  },
  {
    kicker: "Action",
    title: "Act with confidence",
    text: "When change is needed, the assistant guides the next step with approvals, audits, and clear feedback.",
    bullets: ["Safe execution", "Approval flow", "Audit trail"],
    accent: "from-cyan-400/20 to-emerald-500/20",
    terminal: [
      "Scale out api set by 2 instances",
      "Reviewing change...",
      "Done in 47s."
    ]
  },
  {
    kicker: "Coming soon",
    title: "Cost of your Azure resources",
    text: "A softer, more visual cost experience is on the way, with spend summaries and optimization signals.",
    bullets: ["Spend insights", "Trend cards", "Recommendations"],
    accent: "from-blue-400/20 to-slate-500/20",
    terminal: [
      "Top cost drivers this month",
      "Virtual Machines · Azure SQL · Storage",
      "Auto-shutdown recommended"
    ]
  },
  {
    kicker: "Close",
    title: "Start talking to your cloud today",
    text: "Azure OPS AI brings operations, actions, and insights into one elegant conversation.",
    bullets: ["Secure sign-in", "Role-based access", "Built for teams"],
    accent: "from-cyan-400/25 to-blue-500/25",
    terminal: [
      "Sign in with Microsoft",
      "One assistant for the full cloud workflow"
    ]
  }
];

const intervalMs = 6500;

export function PromoVideoPage() {
  const [activeScene, setActiveScene] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveScene((current) => (current + 1) % scenes.length);
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, []);

  const scene = scenes[activeScene];
  const progress = useMemo(() => ((activeScene + 1) / scenes.length) * 100, [activeScene]);

  return (
    <main className="promo-page">
      <div className="promo-page__mesh" aria-hidden="true" />
      <div className="promo-page__glow promo-page__glow--one" aria-hidden="true" />
      <div className="promo-page__glow promo-page__glow--two" aria-hidden="true" />

      <header className="promo-page__topbar">
        <Link to="/" className="promo-page__brand">
          <span className="promo-page__orb">AI</span>
          AzureOPS<span>AI</span>
        </Link>
        <div className="promo-page__topbarActions">
          <span className="promo-page__pill">Animated promo</span>
          <Link to="/" className="promo-page__ghostLink">
            Back to landing
          </Link>
        </div>
      </header>

      <section className="promo-page__hero">
        <div className="promo-page__copy">
          <div className="promo-page__badge">
            <span className="promo-page__badgeDot" />
            45-second promo sequence
          </div>

          <div className="promo-page__sceneTag">{scene.kicker}</div>
          <h1>
            {scene.title.split(" ").slice(0, 2).join(" ")}{" "}
            <span>{scene.title.split(" ").slice(2).join(" ")}</span>
          </h1>
          <p className="promo-page__lead">{scene.text}</p>

          <div className="promo-page__chips">
            {scene.bullets.map((bullet) => (
              <span key={bullet} className="promo-page__chip">
                {bullet}
              </span>
            ))}
          </div>

          <div className="promo-page__controls">
            <Link className="promo-page__primary" to="/">
              Sign in with Microsoft
            </Link>
            <button
              type="button"
              className="promo-page__secondary"
              onClick={() => setActiveScene((current) => (current + 1) % scenes.length)}
            >
              Next scene
            </button>
          </div>

          <div className="promo-page__progress">
            <div className="promo-page__progressBar" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="promo-page__stage">
          <div className="promo-stage">
            <div className="promo-stage__glass promo-stage__glass--large" />
            <div className="promo-stage__glass promo-stage__glass--small" />
            <div className={`promo-stage__panel promo-stage__panel--${activeScene % 3}`}>
              <div className="promo-stage__window">
                <div className="promo-stage__windowBar">
                  <span />
                  <span />
                  <span />
                  <div>Azure OPS AI</div>
                </div>

                <div className="promo-stage__message promo-stage__message--user">
                  <div className="promo-stage__avatar promo-stage__avatar--user">U</div>
                  <div className="promo-stage__bubble promo-stage__bubble--user">{scene.terminal[0]}</div>
                </div>

                <div className="promo-stage__message">
                  <div className="promo-stage__avatar promo-stage__avatar--ai">AI</div>
                  <div className="promo-stage__bubble promo-stage__bubble--ai">
                    {scene.terminal.slice(1).map((line) => (
                      <div key={line}>{line}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="promo-page__timeline" aria-label="Promo scenes">
        {scenes.map((item, index) => (
          <button
            key={item.kicker}
            type="button"
            className={`promo-page__timelineItem${index === activeScene ? " active" : ""}`}
            onClick={() => setActiveScene(index)}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{item.kicker}</strong>
              <p>{item.title}</p>
            </div>
          </button>
        ))}
      </section>
    </main>
  );
}
