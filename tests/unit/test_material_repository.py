
def test_repository_add_and_load_material(empty_material_repo):
    repo = empty_material_repo

    repo.add_material("1.4301BRUS-4.0", "1.4301 brus")

    loaded = repo.load_materials()

    assert loaded == [["1.4301BRUS-4.0", "1.4301 brus"]]