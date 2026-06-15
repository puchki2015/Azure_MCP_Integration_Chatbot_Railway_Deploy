import { useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Spinner } from "../../components/ui/Spinner";
import { formatDate } from "../../utils/formatDate";
import { createCostEstimate, listCostEstimates } from "./costs.api";
import type { CostEstimate } from "./costs.types";

const defaultRawInput = "Estimate the cost for a single Azure VM in West US.";

export function AzureResourceCostsPage() {
  const [rawInput, setRawInput] = useState(defaultRawInput);
  const [resourceType, setResourceType] = useState("Virtual Machine");
  const [resourceName, setResourceName] = useState("prod-vm-01");
  const [region, setRegion] = useState("westus");
  const [currencyCode, setCurrencyCode] = useState("USD");
  const [quantity, setQuantity] = useState("1");
  const [unitName, setUnitName] = useState("hour");
  const [hourlyRate, setHourlyRate] = useState("0.12");
  const [monthlyRate, setMonthlyRate] = useState("87.60");
  const [estimates, setEstimates] = useState<CostEstimate[]>([]);
  const [activeEstimate, setActiveEstimate] = useState<CostEstimate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEstimates = async () => {
    const data = await listCostEstimates();
    setEstimates(data);
    setActiveEstimate(data[0] ?? null);
  };

  useEffect(() => {
    let mounted = true;

    const bootstrap = async () => {
      try {
        setLoading(true);
        const data = await listCostEstimates();
        if (!mounted) {
          return;
        }
        setEstimates(data);
        setActiveEstimate(data[0] ?? null);
      } catch (ex) {
        if (mounted) {
          setError(ex instanceof Error ? ex.message : "Failed to load cost estimates");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSubmit = async () => {
    if (!rawInput.trim()) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const estimate = await createCostEstimate({
        raw_input: rawInput.trim(),
        normalized_request: {
          text: rawInput.trim(),
          resource_type: resourceType,
          region,
          quantity: Number(quantity),
          unit_name: unitName
        },
        region,
        currency_code: currencyCode.toUpperCase(),
        confidence: "manual",
        assumptions: {
          entry_mode: "manual",
          pricing_source: "local_postgres_cache"
        },
        lines: [
          {
            resource_type: resourceType,
            resource_name: resourceName,
            quantity: Number(quantity),
            unit_name: unitName,
            hourly_rate: Number(hourlyRate),
            monthly_rate: Number(monthlyRate),
            lookup_key: {
              service_name: resourceType,
              meter_name: unitName,
              region,
              currency_code: currencyCode.toUpperCase(),
              unit_of_measure: unitName
            },
            matched_exactly: false,
            match_confidence: "manual"
          }
        ]
      });

      setActiveEstimate(estimate);
      await loadEstimates();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to save cost estimate");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="screen-center">
        <Spinner />
      </div>
    );
  }

  return (
    <main className="cost-page">
      <div className="cost-page__mesh" aria-hidden="true" />
      <section className="cost-page__hero">
        <div className="cost-page__badge">
          <span className="cost-page__badge-dot" />
          Live estimate storage
        </div>
        <h1>
          Cost of your <span>Azure resources</span>
        </h1>
        <p className="cost-page__lead">
          Create a cost estimate, store it in Railway Postgres, and review the latest saved totals without leaving
          the chat shell.
        </p>

        {error ? <div className="error-banner">{error}</div> : null}

        <div className="cost-page__cards">
          <Card className="cost-card">
            <span className="cost-card__eyebrow">Estimate input</span>
            <h2>Save a manual estimate</h2>
            <p>These values are persisted as a cost estimate and linked to a lookup key for later pricing refreshes.</p>

            <div className="cost-form">
              <label>
                <span className="cost-form__label">Plain-English request</span>
                <textarea
                  className="input cost-form__textarea"
                  rows={4}
                  value={rawInput}
                  onChange={(event) => setRawInput(event.target.value)}
                />
              </label>
              <div className="cost-form__grid">
                <label>
                  <span className="cost-form__label">Resource type</span>
                  <Input value={resourceType} onChange={(event) => setResourceType(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Resource name</span>
                  <Input value={resourceName} onChange={(event) => setResourceName(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Region</span>
                  <Input value={region} onChange={(event) => setRegion(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Currency</span>
                  <Input value={currencyCode} onChange={(event) => setCurrencyCode(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Quantity</span>
                  <Input value={quantity} onChange={(event) => setQuantity(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Unit</span>
                  <Input value={unitName} onChange={(event) => setUnitName(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Hourly rate</span>
                  <Input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} />
                </label>
                <label>
                  <span className="cost-form__label">Monthly rate</span>
                  <Input value={monthlyRate} onChange={(event) => setMonthlyRate(event.target.value)} />
                </label>
              </div>

              <div className="cost-form__actions">
                <Button onClick={() => void handleSubmit()} disabled={saving}>
                  {saving ? "Saving..." : "Save estimate"}
                </Button>
                <span className="cost-form__hint">Stored in Postgres through the `/costs/estimates` endpoint.</span>
              </div>
            </div>
          </Card>

          <Card className="cost-card cost-card--accent">
            <span className="cost-card__eyebrow">Latest estimate</span>
            {activeEstimate ? (
              <>
                <h2>Estimate #{activeEstimate.id}</h2>
                <p>
                  Total: ${Number(activeEstimate.total_monthly ?? 0).toFixed(2)} / month, $
                  {Number(activeEstimate.total_hourly ?? 0).toFixed(4)} / hour
                </p>
                <ul className="cost-page__list">
                  {activeEstimate.lines.map((line) => (
                    <li key={line.id}>
                      {line.resource_type} {line.resource_name ? `(${line.resource_name})` : ""}: {line.quantity}{" "}
                      {line.unit_name} at ${Number(line.hourly_rate).toFixed(4)}/hr
                    </li>
                  ))}
                </ul>
                <small className="session-summary-card__meta">
                  Saved {formatDate(activeEstimate.created_at)} · status {activeEstimate.status}
                </small>
              </>
            ) : (
              <EmptyState title="No estimates yet" description="Save one estimate to start building history." />
            )}
          </Card>
        </div>

        <div className="cost-page__cards">
          <Card className="cost-card">
            <span className="cost-card__eyebrow">History</span>
            <h2>Recently saved estimates</h2>
            {estimates.length === 0 ? (
              <EmptyState title="No saved estimates" description="Your estimate history will appear here." />
            ) : (
              <div className="session-list">
                {estimates.map((estimate) => (
                  <button
                    key={estimate.id}
                    className={[
                      "session-item",
                      activeEstimate?.id === estimate.id ? "session-item--active" : ""
                    ].join(" ")}
                    onClick={() => setActiveEstimate(estimate)}
                  >
                    <strong>Estimate #{estimate.id}</strong>
                    <span>{estimate.currency_code}</span>
                    <small>{formatDate(estimate.created_at)}</small>
                  </button>
                ))}
              </div>
            )}
          </Card>

          <Card className="cost-card">
            <span className="cost-card__eyebrow">Storage model</span>
            <h2>What gets written</h2>
            <p>
              Each saved estimate is persisted with raw input, normalized request JSON, line items, and the cached
              lookup key needed for future pricing refreshes.
            </p>
          </Card>
        </div>
      </section>
    </main>
  );
}
