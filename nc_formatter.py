"""Main code"""

import re
import sys
from pathlib import Path
from rich.console import Console
from typing import Optional

cons = Console()

CNCFOLDER = Path("./CNCs")
pattern: re.Pattern[str] = re.compile(
    r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?\)?"
)


def get_nc_files(folder: Path) -> list[Path]:
    """Vrací seznam všech .NC souborů v adresáři"""
    if not folder.exists() or not folder.is_dir():
        cons.log(f"Adresář {folder} neexistuje nebo není adresář.", style="red")
        sys.exit(1)

    return [file for file in folder.iterdir() if file.suffix.upper() == ".NC"]


def access_line_4(file_path: Path) -> Optional[str]:
    """Načte 4. řádek souboru, nebo vrátí None pokud neexistuje"""
    with file_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i == 4:
                return line.rstrip("\n")
    return None


def fix_material_format(text: str) -> Optional[str]:
    """
    Vrátí první validní výskyt typu (MA/číslo) nebo (MA/číslo název)
    Oprava odstraní nevalidní části jako pomlčky nebo špatné znaky.
    """
    match = re.search(r"MA/(\d\.\d{4})(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?", text)
    if match:
        return f"({match.group(0)})"
    return None


def write_line_4(file_path: Path, new_line: str) -> None:
    """Přepíše 4. řádek souboru novým textem, pokud má soubor alespoň 4 řádky"""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    if len(lines) >= 4:
        lines[3] = new_line
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        cons.log(
            f"{file_path.name}: Soubor má méně než 4 řádky, nelze upravit.",
            style="yellow",
        )


def process_file(nc_file: Path) -> bool:
    """
    Zpracuje jeden NC soubor - ověří a případně opraví 4. řádek.
    Vrací True pokud došlo ke změně, jinak False.
    """
    line_4 = access_line_4(nc_file)
    if line_4 is None:
        cons.log(f"{nc_file.name}: 4. řádek nenalezen", style="yellow")
        return False

    if pattern.fullmatch(line_4):
        cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
        return False

    fixed_line = fix_material_format(line_4)
    if fixed_line:
        cons.log(f"{nc_file.name}: {line_4} -> opraveno na: {fixed_line}", style="red")
        write_line_4(nc_file, fixed_line)
        return True
    else:
        cons.log(
            f"{nc_file.name}: {line_4} -> incorrect, ale nelze opravit",
            style="bold red",
        )
        return False


def main() -> None:
    cons.rule("[bold blue]Kontrola formátu 4. řádku v NC souborech[/bold blue]")
    nc_files = get_nc_files(CNCFOLDER)
    total_files = len(nc_files)
    count_changed = sum(1 for file in nc_files if process_file(file))

    cons.rule()
    cons.log(f"Celkem souborů: [bold]{total_files}[/bold]")
    cons.log(f"Počet změněných souborů: [bold green]{count_changed}[/bold green]")
    cons.rule()


if __name__ == "__main__":
    main()
