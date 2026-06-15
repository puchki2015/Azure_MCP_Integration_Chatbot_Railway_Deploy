from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_app_user
from app.database.models import CostEstimate
from app.database.models import CostEstimateLine
from app.database.models import PricingLookupKey
from app.database.models import PricingSnapshot
from app.database.models import PriceRefreshRun
from app.database.models import User
from app.database.session import get_db
from app.schemas.costs import CostEstimateCreateRequest
from app.schemas.costs import CostAnalysisRequest
from app.schemas.costs import CostAnalysisResponse
from app.schemas.costs import CostAnalysisEnvelope
from app.schemas.costs import CostEstimateLineResponse
from app.schemas.costs import CostEstimateEnvelope
from app.schemas.costs import CostEstimateResponse
from app.schemas.costs import PriceRefreshRunCreateRequest
from app.schemas.costs import PriceRefreshRunResponse
from app.schemas.costs import PricingLookupKeyResponse
from app.schemas.costs import PricingSnapshotIngestRequest
from app.schemas.costs import PricingSnapshotResponse
from app.schemas.costs import CostResolutionRequest
from app.schemas.costs import CostResolutionResponse
from app.schemas.costs import VmPriceCatalogResponse
from app.schemas.costs import VmPriceOverviewResponse
from app.services.price_cache_service import price_cache_service
from app.services.cost_analysis_service import cost_analysis_service
from app.services.cost_pricing_service import cost_pricing_service

router = APIRouter(
    tags=["Costs"]
)


def _lookup_to_response(lookup: PricingLookupKey) -> PricingLookupKeyResponse:
    return PricingLookupKeyResponse.model_validate(lookup)


def _snapshot_to_response(snapshot: PricingSnapshot) -> PricingSnapshotResponse:
    return PricingSnapshotResponse.model_validate(snapshot)


def _line_to_response(line: CostEstimateLine) -> CostEstimateLineResponse:
    return CostEstimateLineResponse.model_validate(line)


def _estimate_to_response(
    estimate: CostEstimate,
    lines: list[CostEstimateLine] | None = None
) -> CostEstimateResponse:
    estimate_lines = lines if lines is not None else list(getattr(estimate, "lines", []))
    response = CostEstimateResponse.model_validate(estimate)
    response.lines = [_line_to_response(line) for line in estimate_lines]
    return response


def _refresh_run_to_response(run: PriceRefreshRun) -> PriceRefreshRunResponse:
    return PriceRefreshRunResponse.model_validate(run)


def _vm_price_overview_to_response(
    lookup_key: PricingLookupKey,
    snapshot: PricingSnapshot | None,
    snapshot_count: int
) -> VmPriceOverviewResponse:
    return VmPriceOverviewResponse(
        lookup_key=_lookup_to_response(lookup_key),
        current_snapshot=_snapshot_to_response(snapshot) if snapshot else None,
        snapshot_count=snapshot_count
    )


@router.post(
    "/costs/analyze",
    response_model=CostAnalysisResponse
)
async def analyze_cost_request(
    request: CostAnalysisRequest,
    user: User = Depends(get_current_app_user)
):
    _ = user
    return cost_analysis_service.analyze(request.raw_input)


@router.post(
    "/costs/resolve",
    response_model=CostResolutionResponse
)
async def resolve_cost_request(
    request: CostResolutionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    analysis = cost_analysis_service.analyze(request.raw_input)
    if analysis.needs_confirmation and not request.selections:
        return CostAnalysisEnvelope(analysis=analysis)

    _, estimate = cost_pricing_service.create_estimate_from_analysis(
        db=db,
        raw_input=request.raw_input,
        analysis=analysis,
        selections=request.selections,
        user_id=user.id,
        source_session_id=request.source_session_id
    )
    if estimate is None:
        return CostAnalysisEnvelope(analysis=analysis)

    return CostEstimateEnvelope(estimate=estimate)


@router.post(
    "/costs/estimates",
    response_model=CostEstimateResponse
)
async def create_cost_estimate(
    request: CostEstimateCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    estimate = price_cache_service.create_estimate(
        db=db,
        raw_input=request.raw_input,
        normalized_request=request.normalized_request,
        user_id=user.id,
        source_session_id=request.source_session_id,
        region=request.region,
        currency_code=request.currency_code,
        assumptions=request.assumptions,
        confidence=request.confidence
    )

    stored_lines: list[CostEstimateLine] = []
    for line_input in request.lines:
        lookup_key_id = None
        snapshot_id = None

        lookup_spec = line_input.lookup_key
        if lookup_spec:
            lookup_spec = {
                **lookup_spec,
                "currency_code": request.currency_code,
                "region": request.region or lookup_spec.get("region")
            }
            lookup = price_cache_service.get_or_create_lookup_key(
                db=db,
                spec=lookup_spec
            )
            lookup_key_id = lookup.id
            current_snapshot = price_cache_service.get_current_snapshot(
                db=db,
                lookup_key_id=lookup.id
            )
            if current_snapshot:
                snapshot_id = current_snapshot.id

        stored_lines.append(
            price_cache_service.add_estimate_line(
                db=db,
                estimate_id=estimate.id,
                lookup_key_id=lookup_key_id,
                snapshot_id=snapshot_id,
                resource_type=line_input.resource_type,
                resource_name=line_input.resource_name,
                quantity=line_input.quantity,
                unit_name=line_input.unit_name,
                hourly_rate=line_input.hourly_rate,
                monthly_rate=line_input.monthly_rate,
                matched_exactly=line_input.matched_exactly,
                match_confidence=line_input.match_confidence,
                assumptions=line_input.assumptions
            )
        )

    estimate = price_cache_service.finalize_estimate(
        db=db,
        estimate_id=estimate.id
    )
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail="Estimate not found"
        )

    return _estimate_to_response(
        estimate=estimate,
        lines=stored_lines
    )


@router.get(
    "/costs/estimates",
    response_model=list[CostEstimateResponse]
)
async def list_cost_estimates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    estimates = (
        db.query(CostEstimate)
        .filter(CostEstimate.user_id == user.id)
        .order_by(CostEstimate.created_at.desc())
        .all()
    )

    return [
        _estimate_to_response(estimate)
        for estimate in estimates
    ]


@router.get(
    "/costs/estimates/{estimate_id}",
    response_model=CostEstimateResponse
)
async def get_cost_estimate(
    estimate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    estimate = (
        db.query(CostEstimate)
        .filter(
            CostEstimate.id == estimate_id,
            CostEstimate.user_id == user.id
        )
        .first()
    )
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail="Estimate not found"
        )

    return _estimate_to_response(estimate)


@router.get(
    "/costs/lookup-keys",
    response_model=list[PricingLookupKeyResponse]
)
async def list_pricing_lookup_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    _ = user
    lookup_keys = (
        db.query(PricingLookupKey)
        .order_by(PricingLookupKey.last_refresh_at.desc().nullslast())
        .all()
    )
    return [
        _lookup_to_response(lookup_key)
        for lookup_key in lookup_keys
    ]


@router.get(
    "/costs/lookup-keys/{lookup_key_id}/snapshots",
    response_model=list[PricingSnapshotResponse]
)
async def list_pricing_snapshots(
    lookup_key_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    _ = user
    snapshots = (
        db.query(PricingSnapshot)
        .filter(PricingSnapshot.lookup_key_id == lookup_key_id)
        .order_by(PricingSnapshot.fetched_at.desc())
        .all()
    )
    return [
        _snapshot_to_response(snapshot)
        for snapshot in snapshots
    ]


@router.post(
    "/costs/snapshots",
    response_model=PricingSnapshotResponse
)
async def ingest_pricing_snapshot(
    request: PricingSnapshotIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    _ = user

    lookup_key = price_cache_service.get_or_create_lookup_key(
        db=db,
        spec=request.lookup_key
    )
    snapshot = price_cache_service.refresh_lookup_key(
        db=db,
        lookup_key=lookup_key,
        api_url=request.api_url,
        raw_payload=request.raw_payload,
        request_params=request.request_params
    )
    return _snapshot_to_response(snapshot)


@router.post(
    "/costs/refresh-runs",
    response_model=PriceRefreshRunResponse
)
async def create_refresh_run(
    request: PriceRefreshRunCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    run = price_cache_service.start_refresh_run(
        db=db,
        trigger_type=request.trigger_type,
        requested_by=user.email,
        refresh_metadata=request.refresh_metadata or {}
    )
    return _refresh_run_to_response(run)


@router.post(
    "/costs/refresh-vms",
    response_model=PriceRefreshRunResponse
)
async def refresh_all_vm_prices(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    run = cost_pricing_service.refresh_all_vm_prices(
        db=db,
        requested_by=user.email
    )
    return _refresh_run_to_response(run)


@router.get(
    "/costs/vm-prices",
    response_model=VmPriceCatalogResponse
)
async def list_vm_prices(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    _ = user
    base_query = (
        db.query(PricingLookupKey)
        .filter(
            PricingLookupKey.service_name == "Virtual Machines",
            PricingLookupKey.is_active.is_(True)
        )
    )
    total_items = base_query.count()
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = min(page, total_pages)
    offset = (page - 1) * page_size

    lookup_keys = (
        base_query
        .order_by(PricingLookupKey.last_refresh_at.desc().nullslast(), PricingLookupKey.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return VmPriceCatalogResponse(
        items=[
        _vm_price_overview_to_response(
            lookup_key=lookup_key,
            snapshot=price_cache_service.get_current_snapshot(
                db=db,
                lookup_key_id=lookup_key.id
            ),
            snapshot_count=(
                db.query(PricingSnapshot)
                .filter(PricingSnapshot.lookup_key_id == lookup_key.id)
                .count()
            )
        )
        for lookup_key in lookup_keys
        ],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages
    )
