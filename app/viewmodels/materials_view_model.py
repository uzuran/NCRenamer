"""Materials view model"""

class MaterialsViewModel:
    """Simple ViewModel to load CSV data for materials."""

    def __init__(self, app_instance, repo, texts=None):
        self.app = app_instance
        self.repo = repo
        self.texts = texts or {}

    def update_texts(self, texts: dict):
        """Store the current UI texts for translated messages."""
        self.texts = texts or {}

    def get_current_language_name(self, language_names: dict) -> str:
        """Get the display name of the current language."""
        code = self.app.current_language_code
        for name, lang_code in language_names.items():
            if lang_code == code:
                return name
        return "Czech"

    def change_language(self, new_lang_display_name: str):
        """Change the application language."""
        from app.translations.translations import LANGUAGE_NAMES

        new_lang_code = LANGUAGE_NAMES.get(new_lang_display_name)
        if new_lang_code:
            self.app.set_language(new_lang_code)

    def add_material(self, incorrect: str, correct: str):
        """Add a material mapping."""
        incorrect = incorrect.strip()
        correct = correct.strip()

        if not incorrect or not correct:
            return False, self.texts.get("no_empty", "Material cannot be empty.")

        success = self.repo.add_material(incorrect, correct)
        if not success:
            return False, self.texts.get("material_exists", "Material already exists")

        return True, self.texts.get("material_added", "Material added")

    def remove_material(self, incorrect: str):
        """Remove a material mapping."""
        incorrect = incorrect.strip()

        if not incorrect:
            return False, self.texts.get("no_material_selected", "No material selected")

        success = self.repo.delete_material(incorrect)

        if not success:
            return False, self.texts.get("material_not_found", "Material not found")

        return True, self.texts.get("material_removed", "Material removed")

    def get_materials(self):
        "Get materials from model"
        return self.repo.load_materials()
