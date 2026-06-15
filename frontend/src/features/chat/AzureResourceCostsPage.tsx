import { useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { formatDate } from "../../utils/formatDate";
import { analyzeCostRequest, listCostEstimates, listPriceCatalog, refreshVmPrices, resolveCostRequest } from "./costs.api";
import type { CostAnalysis, CostEstimate, PriceCatalog, PriceCatalogService, PriceRefreshRun } from "./costs.types";

const defaultRawInput =
  "Provide me the cost estimates for 100 VMs in east us location of size B4ms and 2 Azure SQL database with minimum configuration.";

type CostsTab = "estimate" | "refresh" | "catalog";

const catalogServices: Array<{ label: string; value: PriceCatalogService }> = [
  { label: "VMs", value: "Virtual Machines" },
  { label: "SQL Database", value: "Azure SQL Database" }
];

type PagerItem = number | "ellipsis";

function buildPagerItems(currentPage: number, totalPages: number): PagerItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const items = new Set<number>([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);
  const pages = Array.from(items)
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((left, right) => left - right);

  const result: PagerItem[] = [];
  for (let index = 0; index < pages.length; index += 1) {
    const page = pages[index];
    const previous = pages[index - 1];
    if (previous && page - previous > 1) {
      result.push("ellipsis");
    }
    result.push(page);
  }

  return result;
}

export function AzureResourceCostsPage() {
  const [activeTab, setActiveTab] = useState<CostsTab>("estimate");
  const [rawInput, setRawInput] = useState(defaultRawInput);
  const [analysis, setAnalysis] = useState<CostAnalysis | null>(null);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [estimates, setEstimates] = useState<CostEstimate[]>([]);
  const [activeEstimate, setActiveEstimate] = useState<CostEstimate | null>(null);
  const [refreshRun, setRefreshRun] = useState<PriceRefreshRun | null>(null);
  const [catalog, setCatalog] = useState<PriceCatalog | null>(null);
  const [catalogService, setCatalogService] = useState<PriceCatalogService>("Virtual Machines");
  const [catalogPage, setCatalogPage] = useState(1);
  const catalogPageSize = 8;
  const [loading, setLoading] = useState(true);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEstimates = async () => {
    const data = await listCostEstimates();
    setEstimates(data);
    setActiveEstimate(data[0] ?? null);
  };

  const loadCatalog = async (serviceName = catalogService, page = catalogPage) => {
    setLoadingCatalog(true);
    setError(null);

    try {
      const data = await listPriceCatalog(serviceName, page, catalogPageSize);
      setCatalog(data);
      setCatalogPage(data.page);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to load VM prices");
    } finally {
      setLoadingCatalog(false);
    }
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

  useEffect(() => {
    if (activeTab === "catalog") {
      void loadCatalog(catalogService, catalogPage);
    }
  }, [activeTab, catalogService, catalogPage]);

  const runAnalysis = async () => {
    if (!rawInput.trim()) {
      setError("Enter a request before analyzing it.");
      return;
    }

    setAnalyzing(true);
    setResolving(false);
    setError(null);

    try {
      const result = await analyzeCostRequest({ raw_input: rawInput.trim() });
      setAnalysis(result);
      setSelections({});

      if (!result.needs_confirmation && result.ready_to_price) {
        await runResolution({});
      }
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to analyze the request");
    } finally {
      setAnalyzing(false);
    }
  };

  const runResolution = async (providedSelections?: Record<string, string>) => {
    setResolving(true);
    setError(null);

    try {
      const result = await resolveCostRequest({
        raw_input: rawInput.trim(),
        selections: providedSelections ?? selections
      });

      if (result.kind === "analysis") {
        setAnalysis(result.analysis);
        return;
      }

      setActiveEstimate(result.estimate);
      await loadEstimates();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to generate the estimate");
    } finally {
      setResolving(false);
    }
  };

  const runVmRefresh = async () => {
    setRefreshing(true);
    setError(null);

    try {
      const result = await refreshVmPrices();
      setRefreshRun(result);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Failed to refresh VM prices");
    } finally {
      setRefreshing(false);
    }
  };

  const handleCatalogPageChange = (page: number) => {
    if (page === catalogPage) {
      return;
    }
    setCatalogPage(page);
  };

  const handleCatalogServiceChange = (service: PriceCatalogService) => {
    if (service === catalogService) {
      return;
    }
    setCatalogService(service);
    setCatalogPage(1);
    setCatalog(null);
  };

  const handleSelectionChange = (fieldName: string, value: string) => {
    setSelections((current) => ({
      ...current,
      [fieldName]: value
    }));
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
          Analyze-first cost flow
        </div>
        <h1>
          Cost of your <span>Azure resources</span>
        </h1>
        <p className="cost-page__lead">
          Describe the infrastructure you want. The backend will first analyze the request, ask for confirmation if
          any pricing-critical field is unclear, and only then create the estimate from cached or live Azure pricing.
        </p>

        <div className="cost-tabs" role="tablist" aria-label="Cost page tabs">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "estimate"}
            className={["cost-tab", activeTab === "estimate" ? "cost-tab--active" : ""].join(" ")}
            onClick={() => setActiveTab("estimate")}
          >
            Estimate flow
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "refresh"}
            className={["cost-tab", activeTab === "refresh" ? "cost-tab--active" : ""].join(" ")}
            onClick={() => setActiveTab("refresh")}
          >
            Refresh VM prices
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "catalog"}
            className={["cost-tab", activeTab === "catalog" ? "cost-tab--active" : ""].join(" ")}
            onClick={() => setActiveTab("catalog")}
          >
            VM catalog
          </button>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}

        {activeTab === "estimate" ? (
          <>
            <div className="cost-page__cards">
              <Card className="cost-card">
                <span className="cost-card__eyebrow">Request input</span>
                <h2>Describe the workload</h2>
                <p>
                  The system extracts resource intents from plain English, flags ambiguities, and shows suggested
                  options before pricing.
                </p>

                <div className="cost-form">
                  <label>
                    <span className="cost-form__label">Plain-English request</span>
                    <textarea
                      className="input cost-form__textarea"
                      rows={6}
                      value={rawInput}
                      onChange={(event) => setRawInput(event.target.value)}
                    />
                  </label>

                  <div className="cost-form__actions">
                    <Button onClick={() => void runAnalysis()} disabled={analyzing || resolving}>
                      {analyzing ? "Analyzing..." : "Analyze request"}
                    </Button>
                    <span className="cost-form__hint">
                      Clarifications are required before pricing ambiguous VM size, OS image, tier, or region inputs.
                    </span>
                  </div>
                </div>
              </Card>

              <Card className="cost-card cost-card--accent">
                <span className="cost-card__eyebrow">Current state</span>
                {analysis ? (
                  <>
                    <h2>{analysis.needs_confirmation ? "Confirmation needed" : "Ready to price"}</h2>
                    <p>{analysis.normalized_text}</p>
                    <ul className="cost-page__list">
                      {analysis.intents.map((intent, index) => (
                        <li key={`${intent.resource_type}-${index}`}>
                          {intent.resource_type}
                          {intent.quantity ? ` x ${intent.quantity}` : ""}
                          {intent.region ? ` in ${intent.region}` : ""}
                          {intent.sku ? ` (${intent.sku})` : ""}
                        </li>
                      ))}
                    </ul>
                    {analysis.assumptions.length > 0 ? (
                      <div className="cost-page__notes">
                        {analysis.assumptions.map((assumption) => (
                          <p key={assumption}>{assumption}</p>
                        ))}
                      </div>
                    ) : null}
                  </>
                ) : (
                  <EmptyState
                    title="No analysis yet"
                    description="Analyze a request to see whether the backend can price it immediately or needs confirmation."
                  />
                )}
              </Card>
            </div>

            {analysis?.clarification_items.length ? (
              <Card className="cost-card">
                <span className="cost-card__eyebrow">Clarifications</span>
                <h2>Confirm the ambiguous fields</h2>
                <p>Select a value for each field below. These values will be passed back to the backend before pricing.</p>

                <div className="cost-form">
                  {analysis.clarification_items.map((item) => (
                    <label key={item.field_name} className="cost-form__field">
                      <span className="cost-form__label">{item.message}</span>
                      <select
                        className="input"
                        value={selections[item.field_name] ?? ""}
                        onChange={(event) => handleSelectionChange(item.field_name, event.target.value)}
                      >
                        <option value="">Select one</option>
                        {item.suggested_values.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </label>
                  ))}

                  <div className="cost-form__actions">
                    <Button
                      onClick={() => void runResolution()}
                      disabled={resolving || analysis.clarification_items.some((item) => !selections[item.field_name])}
                    >
                      {resolving ? "Generating estimate..." : "Confirm and price"}
                    </Button>
                    <span className="cost-form__hint">No estimate is created until the clarifications are confirmed.</span>
                  </div>
                </div>
              </Card>
            ) : null}

            <div className="cost-page__cards">
              <Card className="cost-card">
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
                  <EmptyState
                    title="No estimates yet"
                    description="Confirm a request to generate the first priced estimate."
                  />
                )}
              </Card>

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
            </div>

            <div className="cost-page__cards">
              <Card className="cost-card">
                <span className="cost-card__eyebrow">Storage model</span>
                <h2>What gets written</h2>
                <p>
                  Analysis results stay in the request state until the user confirms. Once priced, the backend writes
                  the estimate, the line items, and the cached pricing snapshot that was used.
                </p>
              </Card>

              <Card className="cost-card">
                <span className="cost-card__eyebrow">Confirmation policy</span>
                <h2>No silent assumptions</h2>
                <p>
                  If the backend cannot confidently infer a pricing-critical field, it returns suggested values and
                  waits for your confirmation before calculating the estimate.
                </p>
              </Card>
            </div>
          </>
        ) : activeTab === "refresh" ? (
          <div className="cost-page__cards">
            <Card className="cost-card">
              <span className="cost-card__eyebrow">VM refresh job</span>
              <h2>Refresh all stored VM prices</h2>
              <p>
                This triggers a backend job that walks all active Virtual Machines lookup keys in Postgres, fetches
                the current Azure Retail Prices row, and stores a new snapshot when the price changed.
              </p>

              <div className="cost-form__actions">
                <Button onClick={() => void runVmRefresh()} disabled={refreshing}>
                  {refreshing ? "Refreshing..." : "Run VM refresh"}
                </Button>
                <span className="cost-form__hint">
                  Use this after changing VM pricing assumptions or when you want to refresh cached VM snapshots.
                </span>
              </div>
            </Card>

            <Card className="cost-card cost-card--accent">
              <span className="cost-card__eyebrow">Latest refresh run</span>
              {refreshRun ? (
                <>
                  <h2>Run #{refreshRun.id}</h2>
                  <p>
                    Status {refreshRun.status} · processed {refreshRun.keys_processed} · refreshed{" "}
                    {refreshRun.keys_refreshed} · unchanged {refreshRun.keys_unchanged} · failed{" "}
                    {refreshRun.keys_failed}
                  </p>
                  {refreshRun.error_summary ? <p>{refreshRun.error_summary}</p> : null}
                  <small className="session-summary-card__meta">
                    Started {formatDate(refreshRun.started_at)} · finished{" "}
                    {refreshRun.finished_at ? formatDate(refreshRun.finished_at) : "in progress"}
                  </small>
                </>
              ) : (
                <EmptyState
                  title="No refresh run yet"
                  description="Run the VM refresh job to update all cached Virtual Machine pricing rows."
                />
              )}
            </Card>
          </div>
        ) : (
          <div className="cost-page__cards">
            <Card className="cost-card cost-card--accent">
              <div className="cost-catalog__header">
                <div>
                  <span className="cost-card__eyebrow">Price catalog</span>
                  <h2>Cached VM and SQL Database prices</h2>
                  <p>
                    Review the cached pricing rows in Postgres. Switch service type, then use the page controls at the
                    bottom to browse the catalog.
                  </p>
                </div>

                <div className="cost-catalog__serviceTabs" role="tablist" aria-label="Catalog services">
                  {catalogServices.map((service) => (
                    <button
                      key={service.value}
                      type="button"
                      className={[
                        "cost-catalog__serviceTab",
                        catalogService === service.value ? "cost-catalog__serviceTab--active" : ""
                      ].join(" ")}
                      onClick={() => handleCatalogServiceChange(service.value)}
                    >
                      {service.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="cost-catalog__summary">
                <div>
                  <strong>{catalog?.total_items ?? 0}</strong>
                  <span>Total cached rows</span>
                </div>
                <div>
                  <strong>{catalog?.page ?? 1}</strong>
                  <span>Current page</span>
                </div>
                <div>
                  <strong>{catalog?.total_pages ?? 1}</strong>
                  <span>Pages available</span>
                </div>
                <div className="cost-catalog__reload">
                  <Button onClick={() => void loadCatalog(catalogService, catalogPage)} disabled={loadingCatalog}>
                    {loadingCatalog ? "Loading..." : "Reload catalog"}
                  </Button>
                  <span className="cost-form__hint">
                    Showing {catalogService === "Virtual Machines" ? "VM" : "SQL Database"} pricing cached in Postgres.
                  </span>
                </div>
              </div>

              {catalog && catalog.items.length === 0 && !loadingCatalog ? (
                <EmptyState
                  title="No cached rows"
                  description={`Run the ${catalogService === "Virtual Machines" ? "VM" : "SQL Database"} refresh job first to populate this catalog.`}
                />
              ) : (
                <>
                  <div className="cost-catalog__panel">
                    <div className="table-scroll">
                      <table className="table cost-catalog__table">
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Region</th>
                            <th>Meter</th>
                            <th>Price</th>
                            <th>Updated</th>
                            <th>Snapshots</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(catalog?.items ?? []).map((item) => (
                            <tr key={item.lookup_key.id}>
                              <td className="cost-catalog__typeCell">
                                <strong>{item.lookup_key.arm_sku ?? item.lookup_key.meter_name ?? "Unknown"}</strong>
                                <div>{item.lookup_key.product_name ?? item.lookup_key.service_name}</div>
                              </td>
                              <td>{item.lookup_key.region ?? "n/a"}</td>
                              <td>{item.lookup_key.meter_name ?? "n/a"}</td>
                              <td>
                                {item.current_snapshot
                                  ? `$${Number(item.current_snapshot.unit_price).toFixed(6)} / ${
                                      item.current_snapshot.unit_of_measure ?? "unit"
                                    }`
                                  : "n/a"}
                              </td>
                              <td>{item.current_snapshot ? formatDate(item.current_snapshot.fetched_at) : "n/a"}</td>
                              <td>{item.snapshot_count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {catalog && catalog.total_pages > 1 ? (
                    <div className="cost-catalog__pagination" aria-label="Catalog pagination">
                      <Button
                        onClick={() => handleCatalogPageChange(Math.max(1, catalog.page - 1))}
                        disabled={loadingCatalog || catalog.page === 1}
                        variant="secondary"
                      >
                        Previous
                      </Button>
                      <div className="cost-catalog__pages" role="navigation" aria-label="Catalog pages">
                        {buildPagerItems(catalog.page, catalog.total_pages).map((item, index) =>
                          item === "ellipsis" ? (
                            <span key={`ellipsis-${index}`} className="cost-catalog__ellipsis" aria-hidden="true">
                              …
                            </span>
                          ) : (
                            <button
                              key={item}
                              type="button"
                              className={[
                                "cost-catalog__page",
                                item === catalog.page ? "cost-catalog__page--active" : ""
                              ].join(" ")}
                              onClick={() => handleCatalogPageChange(item)}
                              disabled={loadingCatalog}
                              aria-current={item === catalog.page ? "page" : undefined}
                            >
                              {item}
                            </button>
                          )
                        )}
                      </div>
                      <Button
                        onClick={() => handleCatalogPageChange(Math.min(catalog.total_pages, catalog.page + 1))}
                        disabled={loadingCatalog || catalog.page === catalog.total_pages}
                        variant="secondary"
                      >
                        Next
                      </Button>
                    </div>
                  ) : null}
                </>
              )}
            </Card>
          </div>
        )}
      </section>
    </main>
  );
}
