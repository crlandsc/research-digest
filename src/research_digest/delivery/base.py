"""Base delivery provider interface."""

from abc import ABC, abstractmethod


class DeliveryProvider(ABC):
    """Abstract base for email/notification delivery."""

    @abstractmethod
    def send(self, subject: str, body_html: str, body_text: str) -> None:
        """Send the digest."""
