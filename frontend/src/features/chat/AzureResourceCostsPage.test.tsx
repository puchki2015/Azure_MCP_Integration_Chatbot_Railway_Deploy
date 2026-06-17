import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AzureResourceCostsPage } from "./AzureResourceCostsPage";

const listCostEstimatesMock = vi.fn();
const analyzeCostRequestMock = vi.fn();
const resolveCostRequestMock = vi.fn();
const refreshVmPricesMock = vi.fn();
const listPriceCatalogMock = vi.fn();

vi.mock("./costs.api", () => ({
  analyzeCostRequest: (...args: unknown[]) => analyzeCostRequestMock(...args),
  listCostEstimates: (...args: unknown[]) => listCostEstimatesMock(...args),
  listPriceCatalog: (...args: unknown[]) => listPriceCatalogMock(...args),
  resolveCostRequest: (...args: unknown[]) => resolveCostRequestMock(...args),
  refreshVmPrices: (...args: unknown[]) => refreshVmPricesMock(...args)
}));

describe("AzureResourceCostsPage", () => {
  beforeEach(() => {
    cleanup();
    listCostEstimatesMock.mockReset();
    analyzeCostRequestMock.mockReset();
    resolveCostRequestMock.mockReset();
    refreshVmPricesMock.mockReset();
    listPriceCatalogMock.mockReset();
  });

  it("asks for confirmation before pricing and then saves the estimate after selection", async () => {
    const pricedEstimate = {
      id: 42,
      user_id: 7,
      source_session_id: 38,
      raw_input:
        "Provide me the cost estimates for 100 VMs in east us location of size B4ms and 2 Azure SQL database with minimum configuration.",
      normalized_request: {
        normalized_text:
          "provide me the cost estimates for 100 vms in eastus location of size b4ms and 2 azure sql database with minimum configuration"
      },
      region: "eastus",
      currency_code: "USD",
      status: "COMPLETE",
      created_at: "2026-06-15T10:12:07Z",
      updated_at: "2026-06-15T10:12:07Z",
      total_hourly: 8.12,
      total_monthly: 5927.6,
      assumptions: {
        clarification_selections: {
          vm_size: "Standard_B4ms",
          sql_tier: "General Purpose"
        }
      },
      confidence: "confirmed",
      lines: [
        {
          id: 88,
          estimate_id: 42,
          lookup_key_id: 12,
          snapshot_id: 51,
          resource_type: "Virtual Machine",
          resource_name: "Standard_B4ms",
          quantity: 100,
          unit_name: "hour",
          hourly_rate: 8,
          monthly_rate: 5840,
          matched_exactly: true,
          match_confidence: "confirmed",
          assumptions: null,
          created_at: "2026-06-15T10:12:07Z"
        }
      ]
    };

    listCostEstimatesMock.mockResolvedValueOnce([]).mockResolvedValueOnce([pricedEstimate]);

    analyzeCostRequestMock.mockResolvedValueOnce({
      raw_input: pricedEstimate.raw_input,
      normalized_text: pricedEstimate.normalized_request.normalized_text,
      intents: [
        {
          resource_type: "Virtual Machine",
          quantity: 100,
          region: "eastus",
          sku: "B4ms",
          os_image: "ubuntu",
          unit_name: "hour",
          confidence: "low"
        },
        {
          resource_type: "Azure SQL Database",
          quantity: 2,
          region: "eastus",
          sku: "minimum",
          os_image: null,
          unit_name: "vCore Hour",
          confidence: "low"
        }
      ],
      needs_confirmation: true,
      clarification_items: [
        {
          field_name: "vm_size",
          message: "VM size is ambiguous. Please confirm the exact SKU you want priced.",
          suggested_values: ["Standard_B4ms", "Standard_D4s_v5"]
        },
        {
          field_name: "sql_tier",
          message: "SQL Database configuration is ambiguous. Please confirm the tier or minimum configuration you want priced.",
          suggested_values: ["General Purpose", "Business Critical"]
        }
      ],
      assumptions: ["Detected ambiguous phrase: minimum configuration"],
      ready_to_price: false
    });

    resolveCostRequestMock.mockResolvedValueOnce({
      kind: "estimate",
      estimate: pricedEstimate
    });

    render(<AzureResourceCostsPage />);

    expect(await screen.findByText(/No estimates yet/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Analyze request/i }));

    expect(await screen.findByText(/Confirmation needed/i)).toBeInTheDocument();
    expect(screen.getByText(/Confirm the ambiguous fields/i)).toBeInTheDocument();
    expect(screen.getByText(/Parsed payload/i)).toBeInTheDocument();

    fireEvent.change(screen.getAllByRole("combobox")[0], {
      target: { value: "Standard_B4ms" }
    });
    fireEvent.change(screen.getAllByRole("combobox")[1], {
      target: { value: "General Purpose" }
    });

    fireEvent.click(screen.getByRole("button", { name: /Confirm and price/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Estimate #42/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/Total: \$5927.60 \/ month/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Estimate #42/i)).toHaveLength(2);
    expect(resolveCostRequestMock).toHaveBeenCalledWith({
      raw_input:
        "Provide me the cost estimates for 100 VMs in east us location of size B4ms and 2 Azure SQL database with minimum configuration.",
      selections: {
        vm_size: "Standard_B4ms",
        sql_tier: "General Purpose"
      }
    });
  });

  it("renders MySQL clarification dropdowns with structured labels and ordering", async () => {
    listCostEstimatesMock.mockResolvedValueOnce([]);

    analyzeCostRequestMock.mockResolvedValueOnce({
      raw_input: "Price Azure Database for MySQL in west us",
      normalized_text: "price azure database for mysql in westus",
      intents: [
        {
          resource_type: "Azure Database for MySQL",
          quantity: 1,
          region: "westus",
          sku: null,
          deployment_model: null,
          compute_generation: null,
          os_image: null,
          unit_name: "vCore Hour",
          confidence: "low"
        }
      ],
      needs_confirmation: true,
      clarification_items: [
        {
          field_name: "compute_generation",
          message: "Choose the MySQL compute generation.",
          suggested_values: ["Edsv5", "Ddsv6", "Gen5"]
        },
        {
          field_name: "deployment_model",
          message: "Choose the MySQL deployment model.",
          suggested_values: ["Flexible Server", "Single Server"]
        },
        {
          field_name: "tier",
          message: "Choose the MySQL pricing tier.",
          suggested_values: ["Business Critical", "General Purpose", "Burstable"]
        },
        {
          field_name: "region",
          message: "Region is required for MySQL pricing.",
          suggested_values: ["westus", "eastus", "uksouth"]
        }
      ],
      assumptions: [],
      ready_to_price: false
    });

    render(<AzureResourceCostsPage />);

    expect(await screen.findByText(/No estimates yet/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Analyze request/i }));

    expect(await screen.findByText(/Confirm the ambiguous fields/i)).toBeInTheDocument();
    expect(screen.getByLabelText("MySQL region")).toBeInTheDocument();
    expect(screen.getByLabelText("MySQL deployment model")).toBeInTheDocument();
    expect(screen.getByLabelText("MySQL tier")).toBeInTheDocument();
    expect(screen.getByLabelText("MySQL compute generation")).toBeInTheDocument();

    const regionSelect = screen.getByLabelText("MySQL region") as HTMLSelectElement;
    const deploymentSelect = screen.getByLabelText("MySQL deployment model") as HTMLSelectElement;
    const tierSelect = screen.getByLabelText("MySQL tier") as HTMLSelectElement;
    const generationSelect = screen.getByLabelText("MySQL compute generation") as HTMLSelectElement;

    expect(within(regionSelect).getAllByRole("option")[1]).toHaveTextContent("eastus");
    expect(within(deploymentSelect).getAllByRole("option")[1]).toHaveTextContent("Single Server");
    expect(within(tierSelect).getAllByRole("option")[1]).toHaveTextContent("Burstable");
    expect(within(generationSelect).getAllByRole("option")[1]).toHaveTextContent("Gen5");
  });

  it("runs the VM refresh job from the refresh tab", async () => {
    listCostEstimatesMock.mockResolvedValueOnce([]);
    refreshVmPricesMock.mockResolvedValueOnce({
      id: 7,
      started_at: "2026-06-15T10:12:00Z",
      finished_at: "2026-06-15T10:13:00Z",
      status: "SUCCESS",
      trigger_type: "manual",
      requested_by: "tester@local",
      keys_processed: 2,
      keys_refreshed: 2,
      keys_unchanged: 0,
      keys_failed: 0,
      error_summary: null,
      refresh_metadata: {
        scope: "virtual_machines"
      }
    });

    render(<AzureResourceCostsPage />);

    expect(await screen.findByText(/No estimates yet/i)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("tab", { name: /Refresh VM prices/i })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Run VM refresh/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Run #7/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/Status SUCCESS/i)).toBeInTheDocument();
    expect(refreshVmPricesMock).toHaveBeenCalledTimes(1);
  });

  it("lists VM and SQL catalogs with bottom pagination", async () => {
    listCostEstimatesMock.mockResolvedValueOnce([]);
    listPriceCatalogMock
      .mockResolvedValueOnce({
        items: [
          {
            lookup_key: {
              id: 12,
              service_name: "Virtual Machines",
              arm_sku: "Standard_B4ms",
              meter_name: "B4ms",
              product_name: "Virtual Machines Bsv2 Series",
              region: "eastus",
              currency_code: "USD",
              unit_of_measure: "1 Hour",
              tier: "Standard",
              normalized_key: "vm-key",
              is_active: true,
              last_checked_at: "2026-06-15T10:12:05Z",
              last_refresh_at: "2026-06-15T10:12:05Z",
              last_snapshot_id: 51
            },
            current_snapshot: {
              id: 51,
              lookup_key_id: 12,
              source: "azure_retail_prices_api",
              source_item_id: "vm-row-001",
              sku_name: "Standard_B4ms",
              product_name: "Virtual Machines Bsv2 Series",
              meter_name: "B4ms",
              region: "eastus",
              currency_code: "USD",
              unit_of_measure: "1 Hour",
              price_type: "Consumption",
              retail_price: 0.08,
              unit_price: 0.08,
              effective_start: null,
              effective_end: null,
              fetched_at: "2026-06-15T10:12:05Z",
              valid_from: null,
              valid_to: null,
              is_current: true,
              payload_hash: "hash-vm-snapshot",
              raw_payload: {},
              api_url: "https://prices.azure.com/api/retail/prices",
              request_params: null
            },
            snapshot_count: 1
          }
        ],
        page: 1,
        page_size: 8,
        total_items: 17,
        total_pages: 9
      })
      .mockResolvedValueOnce({
        items: [
          {
            lookup_key: {
              id: 18,
              service_name: "Virtual Machines",
              arm_sku: "Standard_D4s_v5",
              meter_name: "D4s v5",
              product_name: "Virtual Machines Dsv5 Series",
              region: "eastus",
              currency_code: "USD",
              unit_of_measure: "1 Hour",
              tier: "Standard",
              normalized_key: "vm-key-2",
              is_active: true,
              last_checked_at: "2026-06-15T11:12:05Z",
              last_refresh_at: "2026-06-15T11:12:05Z",
              last_snapshot_id: 62
            },
            current_snapshot: {
              id: 62,
              lookup_key_id: 18,
              source: "azure_retail_prices_api",
              source_item_id: "vm-row-002",
              sku_name: "Standard_D4s_v5",
              product_name: "Virtual Machines Dsv5 Series",
              meter_name: "D4s v5",
              region: "eastus",
              currency_code: "USD",
              unit_of_measure: "1 Hour",
              price_type: "Consumption",
              retail_price: 0.12,
              unit_price: 0.12,
              effective_start: null,
              effective_end: null,
              fetched_at: "2026-06-15T11:12:05Z",
              valid_from: null,
              valid_to: null,
              is_current: true,
              payload_hash: "hash-vm-snapshot-2",
              raw_payload: {},
              api_url: "https://prices.azure.com/api/retail/prices",
              request_params: null
            },
            snapshot_count: 2
          }
        ],
        page: 2,
        page_size: 8,
        total_items: 17,
        total_pages: 3
      })
      .mockResolvedValueOnce({
        items: [
          {
            lookup_key: {
              id: 25,
              service_name: "Azure SQL Database",
              arm_sku: null,
              meter_name: "General Purpose",
              product_name: "Azure SQL Database",
              region: "eastus",
              currency_code: "USD",
              unit_of_measure: "1 vCore Hour",
              tier: "General Purpose",
              normalized_key: "sql-key",
              is_active: true,
              last_checked_at: "2026-06-15T12:12:05Z",
              last_refresh_at: "2026-06-15T12:12:05Z",
              last_snapshot_id: 71
            },
            current_snapshot: {
              id: 71,
              lookup_key_id: 25,
              source: "azure_retail_prices_api",
              source_item_id: "sql-row-001",
              sku_name: null,
              product_name: "Azure SQL Database",
              meter_name: "General Purpose",
              region: "eastus",
              currency_code: "USD",
              unit_of_measure: "1 vCore Hour",
              price_type: "Consumption",
              retail_price: 0.06,
              unit_price: 0.06,
              effective_start: null,
              effective_end: null,
              fetched_at: "2026-06-15T12:12:05Z",
              valid_from: null,
              valid_to: null,
              is_current: true,
              payload_hash: "hash-sql-snapshot",
              raw_payload: {},
              api_url: "https://prices.azure.com/api/retail/prices",
              request_params: null
            },
            snapshot_count: 1
          }
        ],
        page: 1,
        page_size: 8,
        total_items: 4,
        total_pages: 1
      })
      .mockResolvedValueOnce({
        items: [],
        page: 1,
        page_size: 8,
        total_items: 0,
        total_pages: 1
      });

    render(<AzureResourceCostsPage />);

    expect(await screen.findByText(/No estimates yet/i)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("tab", { name: /VM catalog/i })[0]);

    expect(await screen.findByRole("heading", { name: /Cached VM and SQL Database prices/i })).toBeInTheDocument();
    expect(screen.getByText(/Standard_B4ms/i)).toBeInTheDocument();
    expect(screen.getByText(/0.080000 \/ 1 Hour/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^2$/ })).toBeInTheDocument();
    expect(screen.getByText("...", { selector: ".cost-catalog__ellipsis" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /SQL Database/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^2$/ }));

    await waitFor(() => {
      expect(screen.getByText(/Standard_D4s_v5/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/0.120000 \/ 1 Hour/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /SQL Database/i }));

    await waitFor(() => {
      expect(listPriceCatalogMock).toHaveBeenNthCalledWith(3, "Azure SQL Database", 1, 8);
    });

    expect(screen.getByText(/0.060000 \/ 1 vCore Hour/i)).toBeInTheDocument();
    expect(listPriceCatalogMock).toHaveBeenNthCalledWith(1, "Virtual Machines", 1, 8);
    expect(listPriceCatalogMock).toHaveBeenNthCalledWith(2, "Virtual Machines", 2, 8);

    fireEvent.click(screen.getByRole("button", { name: /MySQL/i }));

    await waitFor(() => {
      expect(screen.getByText(/No cached rows/i)).toBeInTheDocument();
    });

    expect(listPriceCatalogMock).toHaveBeenNthCalledWith(4, "Azure Database for MySQL", 1, 8);
  });
});
