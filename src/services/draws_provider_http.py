from __future__ import annotations

import requests

from src.core.draws import draw_from_payload
from src.core.models import Draw

DRAWS_API_URL = "https://euromillions.api.pedromealha.dev/v1/draws"


class HttpDrawsProvider:
    def __init__(self, api_url: str = DRAWS_API_URL, timeout: int = 10) -> None:
        self.api_url = api_url
        self.timeout = timeout

    def fetch_draws(self) -> list[Draw]:
        response = requests.get(self.api_url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []

        draws: list[Draw] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            draw = draw_from_payload(item, source="pedromealha")
            if draw is not None:
                draws.append(draw)
        return draws
