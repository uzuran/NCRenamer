class PasswordModel:
    def __init__(self, correct_password: str):
        self.correct_password = correct_password

    def verify_password(self, password: str) -> bool:
        return password == self.correct_password
