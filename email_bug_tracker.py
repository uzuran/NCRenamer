"Module for handling email functionality in the application."

import os
import json
from rich.console import Console

cons: Console = Console()


class EmailBugTracker:
    """Class that allow users send bugs reports in app."""

    def __init__(self):
        self.counter_file = "email_counter.json"
        self.email_counter = self.load_counter()


    def load_counter(self) -> int:
        """Load the email counter from a JSON file."""
        if os.path.exists(self.counter_file):
            try:
                with open(self.counter_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("counter", 0)
            except (json.JSONDecodeError, KeyError) as e:
                cons.print(
                    f"[red]Chyba při načítání počítadla ze souboru: {e}. Resetuji počítadlo na 0.[/red]"
                )
                return 0
        return 0

    def save_counter(self) -> None:
        """Save the email counter to a JSON file."""
        try:
            with open(self.counter_file, "w", encoding="utf-8") as f:
                json.dump({"counter": self.email_counter}, f)
        except IOError as e:
            cons.print(f"[red]Chyba při ukládání počítadla do souboru: {e}[/red]")