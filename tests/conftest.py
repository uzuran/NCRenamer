# tests/conftest.py
import pytest
from app.models.formatter_model import FormatterModel
from app.models.material_repository import MaterialRepository


class StubMaterialRepository:
    def __init__(self, materials):
        self._materials = materials

    def load_materials(self):
        return self._materials


@pytest.fixture
def formatter_factory():
    def _create(repo=None):
        return FormatterModel(repo)
    return _create


@pytest.fixture
def nc_file_factory(tmp_path):
    def _create(line_4: str):
        nc_file = tmp_path / "sample.NC"
        nc_file.write_text(
            "line1\nline2\nline3\n" + line_4 + "\nline5\n",
            encoding="utf-8"
        )
        return nc_file
    return _create

@pytest.fixture
def empty_material_repo(tmp_path):
    csv_file = tmp_path / "materials.csv"

    csv_file.write_text("")

    return MaterialRepository(csv_path=csv_file)