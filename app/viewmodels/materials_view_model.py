"""Materials view model"""

class MaterialsViewModel:
    """Simple ViewModel to load CSV data for materials."""

    def __init__(self, app_instance, repo):
        self.app = app_instance
        self.repo = repo

    def get_current_language_name(self, language_names: dict) -> str:
        """Get the display name of the current language."""
        code = self.app.current_language_code
        for name, lang_code in language_names.items():
            if lang_code == code:
                return name
        return "Czech"
    
    def add_material(self, incorrect: str, correct: str):
        "Add materials view model"  
        incorrect = incorrect.strip()
        correct = correct.strip()

        if not incorrect or not correct:
            return False, "Materiál nesmí být prázdný"

        success = self.repo.add_material(incorrect, correct)
        if not success:
            return False, "Materiál už existuje"

        return True, "Materiál byl přidán"
    
    def remove_material(self, incorrect: str):
        "Remove material view model"
        incorrect = incorrect.strip()

        if not incorrect:
            return False, "Nebyl vybrán materiál"

        success = self.repo.delete_material(incorrect)

        if not success:
            return False, "Materiál nebyl nalezen"

        return True, "Materiál byl odstraněn"
    
    def get_materials(self):
        "Get materials from model"
        return self.repo.load_materials()