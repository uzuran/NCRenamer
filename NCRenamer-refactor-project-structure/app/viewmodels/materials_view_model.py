class MaterialsViewModel: # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self):
        self.full_history_content = ""

    def set_content(self, content: str): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        self.full_history_content = content

    def search(self, query: str) -> str: # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        query = query.strip().lower()
        if not query:
            return self.full_history_content

        filtered_lines = [
            line for line in self.full_history_content.splitlines()
            if query in line.lower()
        ]
        return "\n".join(filtered_lines)
    
    
