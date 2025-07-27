class MaterialsViewModel:
    def __init__(self):
        self.full_history_content = ""

    def set_content(self, content: str):
        self.full_history_content = content

    def search(self, query: str) -> str:
        query = query.strip().lower()
        if not query:
            return self.full_history_content

        filtered_lines = [
            line for line in self.full_history_content.splitlines()
            if query in line.lower()
        ]
        return "\n".join(filtered_lines)
