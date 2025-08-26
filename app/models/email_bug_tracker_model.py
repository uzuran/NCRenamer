"""Module for handling email functionality in the application."""

import os
import json
from rich.console import Console

cons: Console = Console()


class EmailModel:
    """Class that allows users to send bug reports and tracks the number of reports."""

    def __init__(self, counter_file="json/email_counter.json"):
        self.counter_file = counter_file
        self.email_counter = self.load_counter()

    def load_counter(self) -> int:
        """Load the email counter from a JSON file."""
        if os.path.exists(self.counter_file):
            try:
                with open(self.counter_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("counter", 0)
            except (json.JSONDecodeError, KeyError):
                return 0
        return 0

    def save_counter(self) -> None:
        """Save the email counter to a JSON file."""
        with open(self.counter_file, "w", encoding="utf-8") as f:
            json.dump({"counter": self.email_counter}, f)
            
    def increment_counter(self) -> None:
        """Increments the email counter by one and saves the change."""
        self.email_counter += 1
        self.save_counter()

    def reset_counter(self) -> None:
        """Resets the email counter to 0 and saves the change."""
        self.email_counter = 0
        self.save_counter()