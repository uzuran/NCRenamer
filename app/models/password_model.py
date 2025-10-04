"""A simple password model."""

class PasswordModel:
    """A simple password model for demonstration purposes."""
    def __init__(self, correct_password: str):
        self.correct_password = correct_password

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the correct password."""
        return password == self.correct_password
