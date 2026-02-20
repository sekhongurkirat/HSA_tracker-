from abc import ABC, abstractmethod
from typing import Callable

from models.data_models import EmailMessage


class BaseMonitor(ABC):
    """Abstract base class that all email monitors must implement.

    Any monitor (IMAP IDLE, polling, Gmail push, etc.) plugs into
    the agent by implementing this single interface.
    """

    @abstractmethod
    def start(self, on_message: Callable[[EmailMessage], None]) -> None:
        """Begin monitoring the inbox.

        Args:
            on_message: Callback invoked with each new EmailMessage.
                        The monitor calls this every time a new email arrives.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Gracefully stop monitoring and close connections."""
        ...
