"""Add materials view model"""

class AddMaterialsViewModel:
    """Add materials view model to load CSV data for materials."""

    def __init__(self, app_instance, repo, texts=None):
        self.app = app_instance
        self.repo = repo
        self.texts = texts or {}

    def update_texts(self, texts: dict):
        """Store current UI texts for translated messages."""
        self.texts = texts or {}

    def add_material(self, incorrect: str, correct: str):
        "Add materials view model"  
        incorrect = incorrect.strip()
        correct = correct.strip()

        if not incorrect or not correct:
            return False, self.texts.get("no_empty", "Material cannot be empty.")

        success = self.repo.add_material(incorrect, correct)
        if not success:
            return False, self.texts.get("material_exists", "Material already exists")

        return True, self.texts.get("material_added", "Material added")
    
    def remove_material(self, incorrect: str):
        "Remove material view model"
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
