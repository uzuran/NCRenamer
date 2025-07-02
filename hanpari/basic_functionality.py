from csv import reader, writer
from os import walk, write
from pathlib import Path

# constants
MATERIAL_TABLE_FILE = Path("CNCs/materials_new.csv")
NC_PROGRAMS_DIRECTORY = Path("CNCs")

# types
MATERIALS_TABLE: dict[str, str]
NC_PROGRAM_FILES: set[Path]

# region Dummy or Helper functions


def treat_special_cases(rest: str) -> str:
    if rest[-1:] in "0123456789":
        return rest[:-1]
    return rest.lower()


def correct_material_code(potential_invalid_code: str) -> str:
    number, rest = potential_invalid_code[:6], potential_invalid_code[6:]
    rest, *_ = rest.split("-")
    rest = rest if "." not in rest else ""
    rest = treat_special_cases(rest)
    result = f"{number} {rest.strip()}"
    return result.strip()


def get_nth_line_from_file(file: Path, number_of_line=3):
    with open(file, "r") as f:
        line = next((line for i, line in enumerate(f) if i == number_of_line), None)
    return line.strip() if line else None


# endregion


for dirpath, dirnames, filenames in walk(NC_PROGRAMS_DIRECTORY):
    if dirpath == NC_PROGRAMS_DIRECTORY.name:
        NC_PROGRAM_FILES = set(map(lambda x: NC_PROGRAMS_DIRECTORY / x, filenames))

with open(MATERIAL_TABLE_FILE, "r") as f:
    MATERIALS_TABLE = dict(reader(f, delimiter="\t"))


found_exceptional_cases: list[tuple[str, str, str, str]] = []
counter = 0


for file in NC_PROGRAM_FILES:
    material = get_nth_line_from_file(file)
    if not material:
        raise Exception()
    original = material[4:-1]
    material_number, material_rest = original[:6], original[5:]
    if original in MATERIALS_TABLE:
        corrected = correct_material_code(original)
        if MATERIALS_TABLE[original] != corrected:
            expected = MATERIALS_TABLE[original]
            counter += 1
            found_exceptional_cases.append(
                (original, corrected, expected, "NC programs")
            )


for original in MATERIALS_TABLE:
    corrected = correct_material_code(original)
    expected = MATERIALS_TABLE[original]
    if expected != corrected:
        counter += 1
        found_exceptional_cases.append(
            (original, corrected, expected, "Material table")
        )

with open("hanpari/special_cases.csv", "w") as f:
    w = writer(f, delimiter="|")
    w.writerow(("Original", "Corrected", "Expected"))
    w.writerows(found_exceptional_cases)
