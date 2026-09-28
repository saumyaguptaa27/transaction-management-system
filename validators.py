from datetime import date
from decimal import Decimal, InvalidOperation

TYPES = ["Income", "Expense"]
CATEGORIES = ["Salary", "Food", "Rent", "Travel", "Shopping", "Bills",
              "Health", "Entertainment", "Investment", "Other"]


def validate_transaction(txn_date, description, category, txn_type, amount):
    """Return (clean_dict, errors). errors is a list of messages."""
    errors = []
    description = (description or "").strip()

    if not isinstance(txn_date, date):
        errors.append("Please choose a valid date.")
    elif txn_date > date.today():
        errors.append("Date cannot be in the future.")

    if not description:
        errors.append("Description is required.")
    elif len(description) > 255:
        errors.append("Description must be 255 characters or fewer.")

    if category not in CATEGORIES:
        errors.append("Select a valid category.")
    if txn_type not in TYPES:
        errors.append("Type must be Income or Expense.")

    try:
        amt = Decimal(str(amount)).quantize(Decimal("0.01"))
        if amt <= 0:
            errors.append("Amount must be greater than zero.")
        elif amt > Decimal("9999999999.99"):
            errors.append("Amount is too large.")
    except (InvalidOperation, ValueError, TypeError):
        amt = None
        errors.append("Amount must be a valid number.")

    clean = {"txn_date": txn_date, "description": description,
             "category": category, "txn_type": txn_type, "amount": amt}
    return clean, errors
