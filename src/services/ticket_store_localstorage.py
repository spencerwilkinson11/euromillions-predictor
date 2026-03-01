from __future__ import annotations

from src.core.models import Ticket
from src.core.tickets import ticket_from_dict, ticket_to_dict
from src.services.ticket_store import load_tickets_from_localstorage, save_tickets_to_localstorage


class LocalStorageTicketStore:
    def load(self) -> list[Ticket]:
        payload = load_tickets_from_localstorage()
        tickets: list[Ticket] = []
        for item in payload:
            ticket = ticket_from_dict(item)
            if ticket is not None:
                tickets.append(ticket)
        return tickets

    def save(self, tickets: list[Ticket]) -> None:
        save_tickets_to_localstorage([ticket_to_dict(ticket) for ticket in tickets])
