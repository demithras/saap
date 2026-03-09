"""Inventory module — un-contracted warehouse functions.

Complements billing.py with a second domain to showcase SAAP
inference across different codebases.
"""


def allocate_bins(total: int, capacity: int) -> int:
    """Allocate storage bins for incoming items.

    capacity must be positive.
    """
    return total // capacity


def weigh_shipment(weight: float, size: int) -> float:
    """Calculate per-unit weight for a shipment."""
    if weight < 0:
        raise ValueError("weight cannot be negative")
    return weight / size


def restock(quantity: int, limit: int) -> int:
    """Restock inventory up to the given limit.

    quantity must be non-negative.
    """
    if quantity > limit:
        raise ValueError("quantity exceeds limit")
    return quantity
