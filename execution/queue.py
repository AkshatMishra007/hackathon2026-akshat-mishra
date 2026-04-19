import json
from pathlib import Path
from typing import List

from models.ticket import Ticket


def load_tickets(path: str) -> List[Ticket]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Ticket(
            ticket_id=row["ticket_id"],
            order_id=row.get("order_id"),
            customer_email=row["customer_email"],
            category=row["category"],
            subject=row["subject"],
            message=row["message"],
            requested_amount=row.get("requested_amount"),
            product_id=row.get("product_id"),
            priority_hint=row.get("priority_hint", "normal"),
        )
        for row in data
    ]
