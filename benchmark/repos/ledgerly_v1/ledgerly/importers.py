"""CSV import of historical invoices (moved over from the old billing monolith)."""

import csv
import io


def parse_csv(text: str) -> list[dict]:
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            amount = float(row["amount"])
        except (KeyError, ValueError):
            raise ValueError(f"bad amount in row {row!r}") from None
        rows.append({"invoice_id": row["invoice_id"], "amount": amount})
    return rows
