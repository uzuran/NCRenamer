from pathlib import Path
import sys
import re
from typing import Generator
from rich.console import Console

cons = Console()

CNCFOLDER = Path("./CNCs")
pattern = re.compile(r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?\)?")


def get_nc_files(folder: Path) -> Generator[Path, None, None]:
    """Generuje postupně všechny .NC soubory v adresáři"""
    if not folder.exists() or not folder.is_dir():
        cons.log(f"Adresář {folder} neexistuje nebo není adresář.", style="red")
        sys.exit(1)

    for file in folder.iterdir():
        if file.suffix.upper() == ".NC":
            yield file


def access_line_4(file_path: Path) -> str | None:
    """Načte 4. řádek souboru, nebo vrátí None pokud neexistuje"""
    with file_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i == 4:
                return line.rstrip("\n")
    return None



def fix_material_format(text: str) -> str:
    """
    Vrátí první validní výskyt typu (MA/číslo) nebo (MA/číslo název)
    Oprava odstraní nevalidní části jako pomlčky nebo špatné znaky.
    """
    match = re.search(r"MA/(\d\.\d{4})(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?", text)
    if match:
        full = match.group(0)
        return f"({full})"
    return ""


def write_line_4(file_path: Path, new_line: str) -> None:
    """Přepíše 4. řádek souboru novým textem"""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    lines[3] = new_line
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_file(nc_file: Path) -> bool:
    """
    Zpracuje jeden NC soubor - ověří a případně opraví 4. řádek.
    Vrací True pokud došlo ke změně, jinak False.
    """
    line_4 = access_line_4(nc_file)
    if line_4:
        if pattern.fullmatch(line_4):
            cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
            return False
        else:
            fixed_line = fix_material_format(line_4)
            cons.log(
                f"{nc_file.name}: {line_4} -> incorrect, opravuji na: {fixed_line}",
                style="red",
            )
            write_line_4(nc_file, fixed_line)
            return True
    else:
        cons.log(f"{nc_file.name}: 4. řádek nenalezen", style="yellow")
        return False


def main() -> None:
    cons.rule("Kontrola formátu 4. řádku v NC souborech", style="blue")
    nc_files: list = list(get_nc_files(CNCFOLDER))
    total_files: int = len(nc_files)
    count_changed: int = 0

    for nc_file in nc_files:
        if process_file(nc_file):
            count_changed += 1

    cons.rule()
    cons.log(f"Celkem souborů: {total_files}", style="bold")
    cons.log(f"Počet změněných souborů: {count_changed}", style="bold green")
    cons.rule()


if __name__ == "__main__":
    main()
