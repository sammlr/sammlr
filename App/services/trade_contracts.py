"""Persistent request contract classification, independent of legacy smart markers.

Missing fields in pre-V21 rows mean legacy. Explicit unknown values fail closed.
These helpers do not create requests or implement any lifecycle transitions.
"""

LEGACY_CONTRACT = "legacy"
SMARTDEAL_V1_CONTRACT = "smartdeal_v1"


def request_contract_type(request):
    """Classify a mapping or sqlite3.Row; never infer V1 from status or origin."""
    if request is None or "contract_type" not in request.keys():
        return LEGACY_CONTRACT
    contract_type = request["contract_type"]
    if contract_type not in (LEGACY_CONTRACT, SMARTDEAL_V1_CONTRACT):
        raise ValueError("Unknown request contract type")
    return contract_type


def is_smartdeal_v1_request(request):
    return request_contract_type(request) == SMARTDEAL_V1_CONTRACT


TRADE_LIFECYCLE_V1_CONTRACT = "trade_lifecycle_v1"


def trade_contract_type(connection, trade_id):
    """Resolve a physical trade identity, never a request ID or a status guess.

    New contracts extend trades without rewriting the old request CHECK/contract.
    Missing extension tables are supported on old schemas, never auto-created.
    """
    trade = connection.execute(
        'SELECT legacy_trade_request_id FROM trades WHERE id=?', (trade_id,)
    ).fetchone()
    if trade is None:
        raise ValueError('Unknown trade')
    has_foundation = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lifecycle_contracts'"
    ).fetchone()
    new = connection.execute(
        'SELECT contract_type FROM lifecycle_contracts WHERE trade_id=?', (trade_id,)
    ).fetchone() if has_foundation else None
    if new is not None:
        if trade[0] is not None or new[0] != TRADE_LIFECYCLE_V1_CONTRACT:
            raise ValueError('Conflicting trade contract identity')
        return new[0]
    if trade[0] is None:
        raise ValueError('Trade has no explicit contract owner')
    request = connection.execute('SELECT * FROM trade_requests WHERE id=?', (trade[0],)).fetchone()
    if request is None:
        raise ValueError('Orphaned trade request')
    # Do not depend on the caller's sqlite row_factory.
    columns = [r[1] for r in connection.execute('PRAGMA table_info(trade_requests)')]
    return request_contract_type(dict(zip(columns, request)))


def require_trade_operation(connection, trade_id, operation):
    """Fail closed. Foundation and pre-acceptance requests have explicit owners."""
    kind = trade_contract_type(connection, trade_id)
    allowed = {
        LEGACY_CONTRACT: frozenset({'legacy'}),
        SMARTDEAL_V1_CONTRACT: frozenset({'smartdeal_request'}),
        TRADE_LIFECYCLE_V1_CONTRACT: frozenset({'foundation', 'request'}),
    }
    if operation not in allowed[kind]:
        raise ValueError('Operation does not belong to this trade contract')
    return kind
