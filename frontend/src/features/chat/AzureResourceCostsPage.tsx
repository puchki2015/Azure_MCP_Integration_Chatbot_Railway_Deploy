const plannedSignals = [
  "Subscription-wide cost overview",
  "Top resource groups by spend",
  "Service-level cost trends",
  "Budget alerts and anomaly signals",
  "Optimization recommendations"
];

export function AzureResourceCostsPage() {
  return (
    <main className="cost-page">
      <div className="cost-page__mesh" aria-hidden="true" />
      <section className="cost-page__hero">
        <div className="cost-page__badge">
          <span className="cost-page__badge-dot" />
          Coming soon
        </div>
        <h1>
          Cost of your <span>Azure resources</span>
        </h1>
        <p className="cost-page__lead">
          A softer, more visual experience for understanding cloud spend is on the way. This page will soon help
          you inspect resource costs, identify high-usage services, and spot optimization opportunities in one place.
        </p>

        <div className="cost-page__cards">
          <article className="cost-card">
            <span className="cost-card__eyebrow">Preview</span>
            <h2>What will be here</h2>
            <p>
              A guided view of Azure spend, with clean summaries, alerts, and actionable recommendations tuned for
              operational teams.
            </p>
          </article>

          <article className="cost-card cost-card--accent">
            <span className="cost-card__eyebrow">Planned signals</span>
            <ul className="cost-page__list">
              {plannedSignals.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </div>

        <div className="cost-page__terminal">
          <div className="cost-page__terminalBar">
            <span />
            <span />
            <span />
            <div>feature-preview.sh</div>
          </div>
          <pre className="cost-page__terminalBody">
{`$ az aiops cost-insights show

> Connecting Azure billing signals...
> Building resource hierarchy...
> Preparing a polished spend overview...

Feature coming soon.
Stay tuned for a focused cost experience with softer visuals and clearer insights.`}
          </pre>
        </div>
      </section>
    </main>
  );
}
