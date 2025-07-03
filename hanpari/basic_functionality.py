from csv import reader, writer
from os import walk, write
from pathlib import Path
from typing import TypeAlias

# constants
MATERIAL_TABLE_FILE = Path("CNCs/materials_new.csv")
NC_PROGRAMS_DIRECTORY = Path("CNCs")

# types
Original: TypeAlias = str
Corrected: TypeAlias = str
Expected: TypeAlias = str
Source: TypeAlias = str
MATERIALS_TABLE: dict[Original, Expected]
NC_PROGRAM_FILES: set[Path]

# region Functions


def treat_special_cases(rest: str) -> str:
    if rest[-1:] in "0123456789":
        return rest[:-1]
    return rest.lower()


def correct_material(original: Original) -> Corrected:
    number, rest = original[:6], original[6:]
    rest, *_ = rest.split("-")
    rest = rest if "." not in rest else ""
    rest = treat_special_cases(rest)
    result = f"{number} {rest.strip()}"
    return result.strip()


def get_nth_line_from_file(file: Path, *, line_number=4) -> str | None:
    with open(file, "r") as f:
        line = next((line for i, line in enumerate(f) if i == line_number - 1), None)
    return line.strip() if line else None


def extract_original_material(material_line: str) -> Original:
    """
    Extracts the material code from a line of text.
    Example:
    (MA/1.0037) -> 1.0037
    """
    return material_line[4:-1]


# endregion


for dirpath, dirnames, filenames in walk(NC_PROGRAMS_DIRECTORY):
    if dirpath == NC_PROGRAMS_DIRECTORY.name:
        NC_PROGRAM_FILES = set(
            map(
                lambda x: NC_PROGRAMS_DIRECTORY / x,
                filter(lambda x: x.endswith(".NC"), filenames),
            )
        )

with open(MATERIAL_TABLE_FILE, "r") as f:
    MATERIALS_TABLE = dict(reader(f, delimiter="\t"))


found_exceptional_cases: list[tuple[Original, Corrected, Expected, Source]] = []
processed_original_materials: set[Original] = set()

for file in NC_PROGRAM_FILES:
    material = get_nth_line_from_file(file)
    if not material:
        raise Exception(f"No material found in file: {file.resolve()}")
    original = extract_original_material(material)
    if original in processed_original_materials:
        continue
    material_number, material_rest = original[:6], original[5:]
    corrected = correct_material(original)
    if original in MATERIALS_TABLE:
        if MATERIALS_TABLE[original] != corrected:
            expected = MATERIALS_TABLE[original]
            found_exceptional_cases.append((original, corrected, expected, file.name))
    else:
        found_exceptional_cases.append((original, corrected, "???", file.name))
    processed_original_materials.add(original)


for original in MATERIALS_TABLE:
    if original in processed_original_materials:
        continue
    corrected = correct_material(original)
    expected = MATERIALS_TABLE[original]
    if expected != corrected:
        found_exceptional_cases.append(
            (original, corrected, expected, "Material table")
        )

with open("hanpari/special_cases.csv", "w") as f:
    w = writer(f, delimiter="|")
    w.writerow(("Original", "Corrected", "Expected", "Source"))
    w.writerows(found_exceptional_cases)

print(f"Found {len(found_exceptional_cases)} exceptional cases.")
print("Special cases written to 'hanpari/special_cases.csv'.")
