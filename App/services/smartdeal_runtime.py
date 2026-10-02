"""Explicit application boundary; pure planning readers remain read-only."""
from services.trade_contracts import request_contract_type, LEGACY_CONTRACT
from services.smartdeal_release import SmartDealReleaseService
from services.smartdeal_acceptance import SmartDealAcceptanceService
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.smartdeal_optimizer import SmartDealOptimizer
from services.albums import all_codes


def dispatch_request(connection, request_id, actor, action, *, catalog_provider=all_codes, now_provider=None):
    """None means legacy. Unsupported V1 lifecycle commands never reach legacy."""
    row = connection.execute('SELECT * FROM trade_requests WHERE id=?', (request_id,)).fetchone()
    if request_contract_type(row) == LEGACY_CONTRACT:
        return None
    if type(actor) is not int or actor not in (row['from_user_id'], row['to_user_id']):
        return 'UNAUTHORIZED'
    if action == 'accept':
        return SmartDealAcceptanceService(connection, catalog_provider, now_provider).accept(request_id, actor).code.value
    if action in ('decline', 'withdraw'):
        service = SmartDealReleaseService(connection, now_provider)
        return getattr(service, action)(request_id, actor).code.value
    return 'LIFECYCLE_UNAVAILABLE'


def cleanup(connection, now_provider=None):
    """Explicit lazy runtime sweep. V20 is a no-op; failures abort the caller flow.

    No background work and no hidden writes in the planning domain. The existing
    sweep owns one atomic transaction; accepted and legacy rows are excluded.
    """
    columns = {r['name'] for r in connection.execute('PRAGMA table_info(trade_requests)')}
    if 'contract_type' not in columns:
        return ()
    return SmartDealReleaseService(connection, now_provider).sweep()


def discover(connection, actor, *, catalog_provider=all_codes, now_provider=None):
    """Canonical internal fresh V1 discovery entry; no new public route."""
    cleanup(connection, now_provider)
    inputs = SmartDealPlanningService(connection, catalog_provider, now_provider).build_pairwise_inputs(actor)
    opportunities = SmartDealPairwiseService.from_planning_inputs(inputs)
    return SmartDealOptimizer.optimize(inputs.subject, opportunities)
