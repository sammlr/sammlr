"""Canonical legacy SELECT defaults for pre-V21 databases; no schema writes."""
class LegacyPlanningReadAdapter:
    """Project the existing pre-V21 legacy defaults, without changing SQL storage.

    Only the three SELECT expressions absent on V20 are adapted. All eligibility,
    availability, reservation and incoming rules stay in the canonical reader.
    """
    def __init__(self, connection):
        self.connection = connection
        columns = {r['name'] for r in connection.execute('PRAGMA table_info(trade_requests)')}
        fields = {'contract_type', 'binding_created_at', 'accepted_at'}
        present = fields & columns
        if present and present != fields:
            raise ValueError('Incomplete request contract schema')
        self.legacy = not present

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, sql, parameters=()):
        if self.legacy and 'q.contract_type' in sql:
            sql = sql.replace('q.contract_type', "'legacy' AS contract_type")
            sql = sql.replace('q.binding_created_at', 'NULL AS binding_created_at')
            sql = sql.replace('q.accepted_at', 'NULL AS accepted_at')
        return self.connection.execute(sql, parameters)
