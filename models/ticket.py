from dataclasses import dataclass
from typing import Optional


@dataclass
class Ticket:
    ticket_id: str
    order_id: Optional[str]
    customer_email: str
    category: str
    subject: str
    message: str
    requested_amount: Optional[float] = None
    product_id: Optional[str] = None
    priority_hint: str = "normal"
