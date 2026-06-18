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
  { label: "SQL Database", value: "Azure SQL Database" },
  { label: "MySQL", value: "Azure Database for MySQL" }
];

type PagerItem = number | "ellipsis";

type EstimateLineGroup = {
  resource_type: string;
  lines: CostEstimate["lines"];
  subtotal_hourly: number;
  subtotal_monthly: number;
};

type CandidateRecordSortMode = "api" | "price-asc" | "price-desc";

type ClarificationFieldMeta = {
  title: string;
  description: string;
  placeholder: string;
  optionOrder?: string[];
};

const MYSQL_CLARIFICATION_META: Record<string, ClarificationFieldMeta> = {
  region: {
    title: "MySQL region",
    description: "Choose the Azure region for the pricing lookup.",
    placeholder: "Select region",
    optionOrder: ["eastus", "eastus2", "westus", "westus2", "centralus", "uksouth"]
  },
  deployment_model: {
    title: "MySQL deployment model",
    description: "Select the server deployment style requested by the user.",
    placeholder: "Select deployment model",
    optionOrder: ["Single Server", "Flexible Server"]
  },
  tier: {
    title: "MySQL tier",
    description: "Select the pricing tier for the MySQL deployment.",
    placeholder: "Select tier",
    optionOrder: ["Basic", "Storage", "Burstable", "General Purpose", "Memory Optimized", "Business Critical"]
  },
  compute_generation: {
    title: "MySQL compute generation",
    description: "Choose the compute generation that matches the user request.",
    placeholder: "Select compute generation",
    optionOrder: ["Gen4", "Gen5", "Dsv3", "Dsv5", "Dsv6", "Dasv5", "Dasv6", "Ddsv5", "Ddsv6", "Esv6", "Easv6", "Eadsv5", "Eadsv6", "Edsv5", "Edsv6"]
  }
};

const DEFAULT_CLARIFICATION_META: ClarificationFieldMeta = {
  title: "Confirm the field",
  description: "Select the most accurate value before pricing continues.",
  placeholder: "Select one"
};

const CLARIFICATION_FIELD_ORDER = [
  "region",
  "deployment_model",
  "tier",
  "compute_generation",
  "vm_size",
  "os_image",
  "sql_tier"
];

function getClarificationMeta(fieldName: string): ClarificationFieldMeta {
  return MYSQL_CLARIFICATION_META[fieldName] ?? DEFAULT_CLARIFICATION_META;
}

function sortClarificationItems(items: CostAnalysis["clarification_items"]) {
  return [...items].sort((left, right) => {
    const leftIndex = CLARIFICATION_FIELD_ORDER.indexOf(left.field_name);
    const rightIndex = CLARIFICATION_FIELD_ORDER.indexOf(right.field_name);
    const safeLeftIndex = leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex;
    const safeRightIndex = rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex;

    if (safeLeftIndex !== safeRightIndex) {
      return safeLeftIndex - safeRightIndex;
    }

    return left.field_name.localeCompare(right.field_name);
  });
}

function sortSuggestedValues(fieldName: string, suggestedValues: string[]) {
  const meta = getClarificationMeta(fieldName);
  if (!meta.optionOrder?.length) {
    return suggestedValues;
  }

  const order = new Map(meta.optionOrder.map((value, index) => [value.toLowerCase(), index]));
  return [...suggestedValues].sort((left, right) => {
    const leftIndex = order.get(left.toLowerCase()) ?? Number.MAX_SAFE_INTEGER;
    const rightIndex = order.get(right.toLowerCase()) ?? Number.MAX_SAFE_INTEGER;
    if (leftIndex !== rightIndex) {
      return leftIndex - rightIndex;
    }
    return left.localeCompare(right);
  });
}

function groupEstimateLines(lines: CostEstimate["lines"]): EstimateLineGroup[] {
  const groups = new Map<string, EstimateLineGroup>();

  for (const line of lines) {
    const key = line.resource_type;
    const hourly = Number(line.hourly_rate ?? 0);
    const monthly = Number(line.monthly_rate ?? 0);
    const current = groups.get(key);

    if (!current) {
      groups.set(key, {
        resource_type: line.resource_type,
        lines: [line],
        subtotal_hourly: hourly,
        subtotal_monthly: monthly
      });
      continue;
    }

    current.lines.push(line);
    current.subtotal_hourly += hourly;
    current.subtotal_monthly += monthly;
  }

  return Array.from(groups.values());
}

function getCandidateRecords(assumptions: Record<string, unknown> | null | undefined) {
  const records = assumptions?.candidate_records;
  if (!Array.isArray(records)) {
    return [];
  }

  return records.filter((record): record is Record<string, unknown> => Boolean(record) && typeof record === "object");
}

function sortCandidateRecords(records: Record<string, unknown>[], mode: CandidateRecordSortMode) {
  const sorted = [...records];

  if (mode === "api") {
    return sorted;
  }

  sorted.sort((left, right) => {
    const leftPrice = Number(left.retailPrice ?? left.retail_price ?? 0);
    const rightPrice = Number(right.retailPrice ?? right.retail_price ?? 0);
    return mode === "price-asc" ? leftPrice - rightPrice : rightPrice - leftPrice;
  });

  return sorted;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function renderAssumptionValue(value: unknown): string | null {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return null;
}

function buildAnalysisPayload(analysis: CostAnalysis) {
  return {
    raw_input: analysis.raw_input,
    normalized_text: analysis.normalized_text,
    intents: analysis.intents,
    needs_confirmation: analysis.needs_confirmation,
    clarification_items: analysis.clarification_items,
    assumptions: analysis.assumptions,
    ready_to_price: analysis.ready_to_price
  };
}

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
  const [candidateRecordSort, setCandidateRecordSort] = useState<CandidateRecordSortMode>("api");
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

  const clarificationItems = analysis ? sortClarificationItems(analysis.clarification_items) : [];
  const mysqlClarificationFields = new Set(["region", "deployment_model", "tier", "compute_generation"]);
  const isMysqlClarificationFlow =
    clarificationItems.length > 0 && clarificationItems.every((item) => mysqlClarificationFields.has(item.field_name));
  const groupedEstimateLines = activeEstimate ? groupEstimateLines(activeEstimate.lines) : [];

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
                      Clarifications are required before pricing ambiguous VM size, OS image, region, deployment model,
                      tier, or compute generation inputs.
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
                    <div className="cost-payload">
                      <div className="cost-payload__grid">
                        <div>
                          <strong>Intents</strong>
                          <span>{analysis.intents.length}</span>
                        </div>
                        <div>
                          <strong>Confirmations</strong>
                          <span>{analysis.clarification_items.length}</span>
                        </div>
                        <div>
                          <strong>Ready</strong>
                          <span>{analysis.ready_to_price ? "Yes" : "No"}</span>
                        </div>
                        <div>
                          <strong>Assumptions</strong>
                          <span>{analysis.assumptions.length}</span>
                        </div>
                      </div>

                      <div className="cost-payload__intents">
                        {analysis.intents.map((intent, index) => (
                          <article key={`${intent.resource_type}-${index}`} className="cost-payload__intent">
                            <strong>{intent.resource_type}</strong>
                            <dl>
                              <div>
                                <dt>Quantity</dt>
                                <dd>{intent.quantity ?? "n/a"}</dd>
                              </div>
                              <div>
                                <dt>Region</dt>
                                <dd>{intent.region ?? "n/a"}</dd>
                              </div>
                              <div>
                                <dt>SKU</dt>
                                <dd>{intent.sku ?? "n/a"}</dd>
                              </div>
                              <div>
                                <dt>Deployment</dt>
                                <dd>{intent.deployment_model ?? "n/a"}</dd>
                              </div>
                              <div>
                                <dt>Generation</dt>
                                <dd>{intent.compute_generation ?? "n/a"}</dd>
                              </div>
                              <div>
                                <dt>OS</dt>
                                <dd>{intent.os_image ?? "n/a"}</dd>
                              </div>
                            </dl>
                          </article>
                        ))}
                      </div>

                      <details className="cost-payload__details">
                        <summary>Parsed payload</summary>
                        <pre className="cost-payload__json">{JSON.stringify(buildAnalysisPayload(analysis), null, 2)}</pre>
                      </details>
                    </div>
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

            {clarificationItems.length ? (
              <Card className={["cost-card", isMysqlClarificationFlow ? "cost-card--mysql" : ""].join(" ")}>
                <span className="cost-card__eyebrow">Clarifications</span>
                <h2>Confirm the ambiguous fields</h2>
                {isMysqlClarificationFlow ? (
                  <>
                    <div className="cost-card__subtitle-row">
                      <span className="cost-card__subtitle">MySQL pricing</span>
                      <span className="cost-card__subtitle-note">
                        Structured dropdowns for region, deployment model, tier, and compute generation
                      </span>
                    </div>
                  <div className="cost-field-chips" aria-label="MySQL clarification fields">
                    {clarificationItems.map((item) => {
                      const meta = getClarificationMeta(item.field_name);
                      return (
                        <span key={item.field_name} className="cost-field-chip">
                          {meta.title}
                        </span>
                        );
                      })}
                  </div>
                  </>
                ) : null}
                <p>
                  Select a value for each field below. These values are passed back to the backend before pricing,
                  including MySQL dropdown fields such as deployment model, tier, compute generation, and region.
                </p>

                <div className="cost-form">
                  {clarificationItems.map((item) => {
                    const meta = getClarificationMeta(item.field_name);
                    const suggestedValues = sortSuggestedValues(item.field_name, item.suggested_values);

                    return (
                      <div key={item.field_name} className="cost-form__field cost-form__field--grouped">
                        <div className="cost-form__field-header">
                          <span className="cost-form__label">{meta.title}</span>
                          <p className="cost-form__hint">{meta.description}</p>
                        </div>
                        <select
                          className="input"
                          aria-label={meta.title}
                          value={selections[item.field_name] ?? ""}
                          onChange={(event) => handleSelectionChange(item.field_name, event.target.value)}
                        >
                          <option value="">{meta.placeholder}</option>
                          {suggestedValues.map((value) => (
                            <option key={value} value={value}>
                              {value}
                            </option>
                          ))}
                        </select>
                        {item.message && item.message !== meta.description ? (
                          <small className="cost-form__helper">{item.message}</small>
                        ) : null}
                      </div>
                    );
                  })}

                  <div className="cost-form__actions">
                    <Button
                      onClick={() => void runResolution()}
                      disabled={resolving || clarificationItems.some((item) => !selections[item.field_name])}
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
                    <div className="estimate-breakdown">
                      {groupedEstimateLines.map((group) => (
                        <section key={group.resource_type} className="estimate-breakdown__group">
                          <div className="estimate-breakdown__groupHeader">
                            <div>
                              <h3>
                                {group.resource_type}
                                {group.lines[0]?.resource_name ? (
                                  <span className="estimate-breakdown__groupTitleMeta">
                                    {group.lines[0].resource_name}
                                  </span>
                                ) : null}
                              </h3>
                              <p>
                                {group.resource_type} priced as{" "}
                                {group.lines.length === 1 ? "1 record" : `${group.lines.length} records`}
                              </p>
                            </div>
                            <div className="estimate-breakdown__groupTotals">
                              <strong>${group.subtotal_monthly.toFixed(2)} / month</strong>
                              <span>${group.subtotal_hourly.toFixed(4)} / hour</span>
                            </div>
                          </div>

                          <div className="estimate-breakdown__lines">
                            {group.lines.map((line, index) => (
                              (() => {
                                const assumptions = line.assumptions as Record<string, unknown> | null;
                                const lookupKey = assumptions?.lookup_key as Record<string, unknown> | undefined;
                                const candidateRecords = sortCandidateRecords(getCandidateRecords(assumptions), candidateRecordSort);

                                return (
                              <article key={line.id} className="estimate-breakdown__line">
                                <div className="estimate-breakdown__lineMain">
                                  <strong>
                                    Record {index + 1}
                                    {line.resource_name ? ` - ${line.resource_name}` : ""}
                                  </strong>
                                  <span>
                                    {line.quantity} {line.unit_name} at ${Number(line.hourly_rate).toFixed(4)}/hr
                                  </span>
                                  <span>${Number(line.monthly_rate).toFixed(2)}/mo</span>
                                </div>
                                <div className="estimate-breakdown__linePricing">
                                  <span className={line.matched_exactly ? "badge badge--success" : "badge badge--warning"}>
                                    {line.matched_exactly ? "Exact match" : "Best match"}
                                  </span>
                                  {line.match_confidence ? <span>{line.match_confidence}</span> : null}
                                </div>
                                {assumptions ? (
                                  <details className="estimate-breakdown__lineDetails">
                                    <summary>Pricing details</summary>
                                    <dl className="estimate-breakdown__detailGrid">
                                      {asString(assumptions.resolution_source) ? (
                                        <div>
                                          <dt>Resolution</dt>
                                          <dd>{asString(assumptions.resolution_source)}</dd>
                                        </div>
                                      ) : null}
                                      {renderAssumptionValue(assumptions.unit_price) ? (
                                        <div>
                                          <dt>Unit price</dt>
                                          <dd>${Number(assumptions.unit_price).toFixed(6)}</dd>
                                        </div>
                                      ) : null}
                                      {renderAssumptionValue(assumptions.quantity) ? (
                                        <div>
                                          <dt>Quantity</dt>
                                          <dd>{renderAssumptionValue(assumptions.quantity)}</dd>
                                        </div>
                                      ) : null}
                                      {lookupKey ? (
                                        <>
                                          {asString(lookupKey.product_name) ? (
                                            <div>
                                              <dt>Product</dt>
                                              <dd>{asString(lookupKey.product_name)}</dd>
                                            </div>
                                          ) : null}
                                          {asString(lookupKey.region) ? (
                                            <div>
                                              <dt>Region</dt>
                                              <dd>{asString(lookupKey.region)}</dd>
                                            </div>
                                          ) : null}
                                          {asString(lookupKey.tier) ? (
                                            <div>
                                              <dt>Tier</dt>
                                              <dd>{asString(lookupKey.tier)}</dd>
                                            </div>
                                          ) : null}
                                        </>
                                      ) : null}
                                      {asString(assumptions.deployment_model) ? (
                                        <div>
                                          <dt>Deployment</dt>
                                          <dd>{asString(assumptions.deployment_model)}</dd>
                                        </div>
                                      ) : null}
                                      {asString(assumptions.compute_generation) ? (
                                        <div>
                                          <dt>Generation</dt>
                                          <dd>{asString(assumptions.compute_generation)}</dd>
                                        </div>
                                      ) : null}
                                      {asString(assumptions.tier) ? (
                                        <div>
                                          <dt>Tier</dt>
                                          <dd>{asString(assumptions.tier)}</dd>
                                        </div>
                                      ) : null}
                                    </dl>
                                  </details>
                                ) : null}
                                {candidateRecords.length > 1 ? (
                                  <details className="estimate-breakdown__lineDetails estimate-breakdown__lineDetails--records">
                                    <summary>All returned Azure records</summary>
                                    <div className="estimate-breakdown__recordToolbar" role="toolbar" aria-label="Candidate record sort order">
                                      <span>Order by</span>
                                      <button
                                        type="button"
                                        className={[
                                          "estimate-breakdown__sortButton",
                                          candidateRecordSort === "api" ? "estimate-breakdown__sortButton--active" : ""
                                        ].join(" ")}
                                        onClick={() => setCandidateRecordSort("api")}
                                      >
                                        API order
                                      </button>
                                      <button
                                        type="button"
                                        className={[
                                          "estimate-breakdown__sortButton",
                                          candidateRecordSort === "price-asc" ? "estimate-breakdown__sortButton--active" : ""
                                        ].join(" ")}
                                        onClick={() => setCandidateRecordSort("price-asc")}
                                      >
                                        Price low to high
                                      </button>
                                      <button
                                        type="button"
                                        className={[
                                          "estimate-breakdown__sortButton",
                                          candidateRecordSort === "price-desc" ? "estimate-breakdown__sortButton--active" : ""
                                        ].join(" ")}
                                        onClick={() => setCandidateRecordSort("price-desc")}
                                      >
                                        Price high to low
                                      </button>
                                    </div>
                                    <div className="estimate-breakdown__recordTableWrap">
                                      <table className="estimate-breakdown__recordTable">
                                        <thead>
                                          <tr>
                                            <th>Record</th>
                                            <th>Product</th>
                                            <th>Meter</th>
                                            <th>SKU</th>
                                            <th>Region</th>
                                            <th>Unit</th>
                                            <th>Type</th>
                                            <th className="estimate-breakdown__recordTablePrice">Price</th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {candidateRecords.map((record, recordIndex) => (
                                            <tr
                                              key={`${line.id}-record-${recordIndex}`}
                                              className={recordIndex === 0 ? "estimate-breakdown__recordRow--selected" : ""}
                                            >
                                              <td>
                                                <span className="estimate-breakdown__recordLabel">
                                                  Record {recordIndex + 1}
                                                </span>
                                                {recordIndex === 0 ? (
                                                  <span className="badge badge--success estimate-breakdown__recordBadge">
                                                    Selected
                                                  </span>
                                                ) : null}
                                              </td>
                                              <td>{asString(record.productName) ? (record.productName as string) : "N/A"}</td>
                                              <td>{asString(record.meterName) ? (record.meterName as string) : "N/A"}</td>
                                              <td>{asString(record.skuName) ? (record.skuName as string) : "N/A"}</td>
                                              <td>{asString(record.armRegionName) ? (record.armRegionName as string) : "N/A"}</td>
                                              <td>{asString(record.unitOfMeasure) ? (record.unitOfMeasure as string) : "N/A"}</td>
                                              <td>{asString(record.type) ? (record.type as string) : "N/A"}</td>
                                              <td className="estimate-breakdown__recordTablePrice">
                                                {asString(record.retailPrice) ? `$${Number(record.retailPrice).toFixed(6)}` : "N/A"}
                                              </td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </details>
                                ) : null}
                              </article>
                                );
                              })()
                            ))}
                          </div>
                        </section>
                      ))}
                    </div>
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
                    Showing{" "}
                    {catalogService === "Virtual Machines"
                      ? "VM"
                      : catalogService === "Azure SQL Database"
                        ? "SQL Database"
                        : "MySQL"}
                    {" "}
                    pricing cached in Postgres.
                  </span>
                </div>
              </div>

              {catalog && catalog.items.length === 0 && !loadingCatalog ? (
                <EmptyState
                  title="No cached rows"
                  description={`Run the ${
                    catalogService === "Virtual Machines"
                      ? "VM"
                      : catalogService === "Azure SQL Database"
                        ? "SQL Database"
                        : "MySQL"
                  } refresh job first to populate this catalog.`}
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
                              ...
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
