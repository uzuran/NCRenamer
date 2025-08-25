"""
Service for persisting and managing the email bug tracker counter.

Handles reading and writing the counter to a JSON file, so the
application state persists across restarts.
"""

import os
import json
from rich.console import Console

CONS = Console()


class EmailService:
    """
    Provides persistence and management for the email bug report counter.
    """

    def __init__(self, file_path: str = "json/email_counter.json"):
        """
        Initialize the service with a file for storing the counter.

        Args:
            file_path (str): Path to the JSON file storing the counter.
        """
        self.file_path = file_path

    def load_counter(self) -> int:
        """
        Load the email counter from a JSON file.

        Returns:
            int: The current counter value (0 if the file is missing or invalid).
        """
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("counter", 0)
            except (json.JSONDecodeError, KeyError) as e:
                CONS.print(
                    f"[red]Chyba při načítání počítadla: {e}. Resetuji počítadlo na 0.[/red]"
                )
        return 0

    def save_counter(self, value: int) -> None:
        """
        Save the email counter to a JSON file.

        Args:
            value (int): The counter value to save.
        """
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"counter": value}, f)
        except IOError as e:
            CONS.print(f"[red]Chyba při ukládání počítadla: {e}[/red]")
