"""Email Bug Tracker ViewModel Module"""
from rich.console import Console
from app.models.email_bug_tracker_model import EmailModel
from tkinter import messagebox
class EmailBugTrackerViewModel:
    """Initialize the ViewModel with the model and console for UI output."""
    def __init__(self, model:EmailModel, console: Console):
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
         messagebox.showerror(
            title="Saving Error",
            message=f"Failed to save the counter. Error: {e}"
        )
         
            