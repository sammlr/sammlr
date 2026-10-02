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
