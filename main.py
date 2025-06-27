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
    """Opraví formát materiálu podle regexu"""
    fixed = re.sub(r"\(MA/(\d\.\d{4})[^\s)]*", r"(MA/\1", text)
    if not fixed.endswith(")"):
        fixed += ")"
    return fixed


def write_line_4(file_path: Path, new_line: str) -> None:
    """Přepíše 4. řádek souboru novým textem"""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    if len(lines) >= 4:
        lines[3] = new_line
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        cons.log(
            f"{file_path.name}: Soubor má méně než 4 řádky, nelze upravit.",
            style="yellow",
        )


def process_file(nc_file: Path) -> None:
    """Zpracuje jeden NC soubor - ověří a případně opraví 4. řádek"""
    line_4 = access_line_4(nc_file)
    if line_4:
        if pattern.fullmatch(line_4):
            cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
        else:
            fixed_line = fix_material_format(line_4)
            cons.log(
                f"{nc_file.name}: {line_4} -> incorrect, opravuji na: {fixed_line}",
                style="red",
            )
            write_line_4(nc_file, fixed_line)
    else:
        cons.log(f"{nc_file.name}: 4. řádek nenalezen", style="yellow")


def main():
    cons.rule("[bold blue]Kontrola formátu 4. řádku v NC souborech[/bold blue]")
    nc_files = get_nc_files(CNCFOLDER)
    for nc_file in nc_files:
        process_file(nc_file)
    cons.rule()


if __name__ == "__main__":
    main()
