from rich.console import Console
from app.models.email_bug_tracker_model import EmailBugTrackerModel

class EmailBugTrackerViewModel:
    """Initialize the ViewModel with the model and console for UI output."""
    def __init__(self, model: EmailBugTrackerModel, console: Console):
        self.model = model
        self.console = console

    @property
    def counter(self):
        """Return the current email counter value."""
        return self.model.email_counter

    def increment_counter(self):
        """Increment the email counter and save the updated value."""
        self.model.email_counter += 1
        try:
            self.model.save_counter()
        except (IOError, OSError) as e:
            self.console.print(f"[red]Error saving counter: {e}[/red]")
            