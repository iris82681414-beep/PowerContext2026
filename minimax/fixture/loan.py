"""Loan renewal business rules."""

def renewal_days(*, member: bool, has_reservation: bool) -> int:
    if has_reservation:
        return 0
    return 14
