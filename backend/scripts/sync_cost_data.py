import argparse
import json
import os
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.base import Base
from app.database.models import ChatSession
from app.database.models import CostEstimate
from app.database.models import PriceRefreshRun
from app.database.models import User
from app.database.session import SessionLocal
from app.database.session import engine
from app.services.azure_retail_prices_service import RetailPriceQuery
from app.services.azure_retail_prices_service import azure_retail_prices_service
from app.services.price_cache_service import price_cache_service


SAMPLE_USER_EMAIL = "costs.sync@local"
SAMPLE_USER_OID = "sync-costs-user-oid"
SAMPLE_ESTIMATE_INPUT = (
    "Estimate a small web app stack with one VM, one app service, one managed disk, "
    "storage, and bandwidth."
)


TARGETS = [
    {
        "name": "Virtual Machine",
        "quantity": 730,
        "unit_name": "hour",
        "query_attempts": [
            RetailPriceQuery(
                service_name="Virtual Machines",
                arm_region_name="westus",
                arm_sku_name="Standard_B2s",
                sku_name="B2s",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_family="Compute",
                arm_region_name="westus",
                arm_sku_name="Standard_B2s",
                currency_code="USD"
            )
        ]
    },
    {
        "name": "App Service",
        "quantity": 730,
        "unit_name": "hour",
        "query_attempts": [
            RetailPriceQuery(
                service_name="Azure App Service",
                arm_region_name="westus",
                arm_sku_name="B1",
                sku_name="B1",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_family="Web",
                arm_region_name="westus",
                arm_sku_name="B1",
                currency_code="USD"
            )
        ]
    },
    {
        "name": "Managed Disk",
        "quantity": 1,
        "unit_name": "month",
        "query_attempts": [
            RetailPriceQuery(
                service_name="Managed Disks",
                arm_region_name="westus",
                arm_sku_name="Premium_SSD_P10",
                sku_name="P10",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_family="Storage",
                arm_region_name="westus",
                arm_sku_name="Premium_SSD_P10",
                currency_code="USD"
            )
        ]
    },
    {
        "name": "Storage Account",
        "quantity": 200,
        "unit_name": "GB-month",
        "query_attempts": [
            RetailPriceQuery(
                service_name="Storage",
                arm_region_name="westus",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_family="Storage",
                product_name="Azure Blob Storage",
                meter_name="Hot LRS Data Stored",
                arm_region_name="westus",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_name="Azure Blob Storage",
                arm_region_name="westus",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_family="Storage",
                arm_region_name="westus",
                currency_code="USD"
            )
        ]
    },
    {
        "name": "Bandwidth",
        "quantity": 500,
        "unit_name": "GB",
        "query_attempts": [
            RetailPriceQuery(
                service_name="Data Transfer",
                arm_region_name="westus",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_name="Bandwidth",
                service_family="Networking",
                arm_region_name="westus",
                currency_code="USD"
            ),
            RetailPriceQuery(
                product_name="Bandwidth",
                arm_region_name="westus",
                currency_code="USD"
            ),
            RetailPriceQuery(
                service_family="Networking",
                arm_region_name="westus",
                currency_code="USD"
            )
        ]
    }
]


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ensure_sample_user(db):
    user = (
        db.query(User)
        .filter(User.email == SAMPLE_USER_EMAIL)
        .first()
    )

    if user:
        return user

    user = User(
        entra_oid=SAMPLE_USER_OID,
        email=SAMPLE_USER_EMAIL,
        display_name="Cost Sync User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_sample_session(db, user: User):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .first()
    )

    if session:
        return session

    session = ChatSession(
        user_id=user.id,
        status="ACTIVE"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def normalize_lookup_spec(item: dict) -> dict:
    return {
        "service_name": item.get("serviceName") or "",
        "arm_sku": item.get("armSkuName") or item.get("skuName"),
        "meter_name": item.get("meterName"),
        "product_name": item.get("productName"),
        "region": item.get("armRegionName") or item.get("location"),
        "currency_code": item.get("currencyCode") or "USD",
        "unit_of_measure": item.get("unitOfMeasure"),
        "tier": item.get("skuName") or item.get("armSkuName")
    }


def derive_rates(snapshot, quantity: float) -> tuple[float, float]:
    unit_price = float(snapshot.unit_price or 0)
    unit_measure = (snapshot.unit_of_measure or "").lower()

    if "hour" in unit_measure:
        hourly_rate = unit_price * quantity
        monthly_rate = hourly_rate * 730
        return hourly_rate, monthly_rate

    monthly_rate = unit_price * quantity
    hourly_rate = monthly_rate / 730 if monthly_rate else 0
    return hourly_rate, monthly_rate


def main():
    parser = argparse.ArgumentParser(description="Sync live Azure Retail Prices into the database.")
    parser.add_argument(
        "--show",
        action="store_true",
        help="Print inserted records after syncing."
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = ensure_sample_user(db)
        session = ensure_sample_session(db, user)
        run = price_cache_service.start_refresh_run(
            db=db,
            trigger_type="seed",
            requested_by=SAMPLE_USER_EMAIL,
            refresh_metadata={
                "sync": True,
                "source": "backend/scripts/sync_cost_data.py"
            }
        )

        estimate = (
            db.query(CostEstimate)
            .filter(
                CostEstimate.user_id == user.id,
                CostEstimate.raw_input == SAMPLE_ESTIMATE_INPUT
            )
            .first()
        )
        if not estimate:
            estimate = price_cache_service.create_estimate(
                db=db,
                raw_input=SAMPLE_ESTIMATE_INPUT,
                normalized_request={
                    "kind": "live-sync",
                    "region": "westus"
                },
                user_id=user.id,
                source_session_id=session.id,
                region="westus",
                currency_code="USD",
                assumptions={
                    "mode": "live-sync",
                    "source": "Azure Retail Prices API"
                },
                confidence="live"
            )

        created_lookup_keys = 0
        created_snapshots = 0
        added_lines = 0

        for target in TARGETS:
            best_item = None
            all_items = []
            api_url = ""
            request_params = {}

            for query in target["query_attempts"]:
                candidate, items, candidate_api_url, candidate_request_params = azure_retail_prices_service.fetch_best_item(query)
                if candidate:
                    best_item = candidate
                    all_items = items
                    api_url = candidate_api_url
                    request_params = candidate_request_params
                    break

            if not best_item:
                run.keys_failed += 1
                run.error_summary = (
                    f"{run.error_summary}\n{target['name']}: no matching Azure price record"
                    if run.error_summary
                    else f"{target['name']}: no matching Azure price record"
                )
                continue

            lookup_spec = normalize_lookup_spec(best_item)
            lookup_key = price_cache_service.get_or_create_lookup_key(
                db=db,
                spec=lookup_spec
            )
            created_lookup_keys += 1

            snapshot = price_cache_service.refresh_lookup_key(
                db=db,
                lookup_key=lookup_key,
                api_url=api_url,
                raw_payload=best_item,
                request_params={
                    **request_params,
                    "query_attempts": [q.__dict__ for q in target["query_attempts"]],
                    "candidate_count": len(all_items)
                }
            )
            created_snapshots += 1

            hourly_rate, monthly_rate = derive_rates(snapshot, target["quantity"])
            price_cache_service.add_estimate_line(
                db=db,
                estimate_id=estimate.id,
                lookup_key_id=lookup_key.id,
                snapshot_id=snapshot.id,
                resource_type=target["name"],
                resource_name=f"sample-{target['name'].lower().replace(' ', '-')}",
                quantity=target["quantity"],
                unit_name=target["unit_name"],
                hourly_rate=hourly_rate,
                monthly_rate=monthly_rate,
                matched_exactly=True,
                match_confidence="live",
                assumptions={
                    "seeded_from_live_api": True,
                    "serviceName": best_item.get("serviceName"),
                    "skuName": best_item.get("skuName"),
                    "meterName": best_item.get("meterName")
                }
            )
            added_lines += 1

        estimate = price_cache_service.finalize_estimate(
            db=db,
            estimate_id=estimate.id
        )

        run.keys_processed = created_lookup_keys
        run.keys_refreshed = created_snapshots
        run.keys_unchanged = 0
        run.keys_failed = run.keys_failed or 0
        run.status = "SUCCESS" if run.keys_failed == 0 else "PARTIAL"
        run.finished_at = utc_now()
        db.commit()
        db.refresh(run)

        print("Sync complete.")
        print(f"User: {user.email} (id={user.id})")
        print(f"Chat session: {session.id}")
        print(f"Refresh run: {run.id}")
        print(f"Lookup keys synced: {created_lookup_keys}")
        print(f"Snapshots synced: {created_snapshots}")
        print(f"Estimate lines added: {added_lines}")
        print(f"Estimate: {estimate.id}")

        if args.show:
            print("\nEstimate payload:")
            print(json.dumps({
                "id": estimate.id,
                "raw_input": estimate.raw_input,
                "total_hourly": float(estimate.total_hourly or 0),
                "total_monthly": float(estimate.total_monthly or 0),
                "lines": [
                    {
                        "resource_type": line.resource_type,
                        "resource_name": line.resource_name,
                        "quantity": float(line.quantity),
                        "unit_name": line.unit_name,
                        "hourly_rate": float(line.hourly_rate),
                        "monthly_rate": float(line.monthly_rate),
                        "lookup_key_id": line.lookup_key_id,
                        "snapshot_id": line.snapshot_id
                    }
                    for line in estimate.lines
                ]
            }, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
