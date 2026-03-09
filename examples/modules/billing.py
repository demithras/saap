"""Billing module — un-contracted financial functions.

Each function is designed to trigger specific SAAP inference heuristics:
name-based, docstring, guard clause, division, and return-type analysis.
"""


def calculate_line_total(quantity: int, unit_price: float) -> float:
    """Calculate total for a single line item.

    quantity must be positive.
    """
    return quantity * unit_price


def apply_discount(amount: float, discount_rate: float) -> float:
    """Apply a percentage discount to an amount."""
    if amount < 0:
        raise ValueError("amount cannot be negative")
    if discount_rate >= 1.0:
        raise ValueError("discount_rate must be less than 1.0")
    return amount * (1 - discount_rate)


def split_payment(total: float, num: int) -> float:
    """Split a total evenly across payers.

    num must be positive.
    """
    return total / num


def calculate_tax(amount: float, tax_rate: float, divisor: float) -> float:
    """Calculate tax, optionally dividing by a scaling divisor."""
    return (amount * tax_rate) / divisor


def generate_invoice_id(count: int) -> str:
    """Generate sequential invoice identifier.

    count must be non-negative.
    """
    return f"INV-{count:06d}"
