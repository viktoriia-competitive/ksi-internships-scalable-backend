class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class TransactionConflict(Exception):
    """Persistence reported a uniqueness/concurrency conflict at commit time."""
