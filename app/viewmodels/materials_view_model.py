class MaterialsViewModel:  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self):
        self.materials_content = ""

    def set_content(
        self, content: str
    ):  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        self.materials_content = content

    def search(
        self, query: str
    ) -> str:  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        query = query.strip().lower()
        if not query:
            return self.materials_content

        filtered_lines = [
            line
            for line in self.materials_content.splitlines()
            if query in line.lower()
        ]
        return "\n".join(filtered_lines)
