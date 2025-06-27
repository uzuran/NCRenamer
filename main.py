from pathlib import Path
import sys
import re
from typing import Generator
from rich.console import Console

cons: Console = Console()

CNCFOLDER: Path = Path("./CNCs")
pattern = re.compile(r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?\)?")

if not CNCFOLDER.exists() or not CNCFOLDER.is_dir():
    cons.log(f"adresar: {CNCFOLDER} neexistuje, koncim program!", style="red")
    sys.exit()

def get_nc_files(folder: Path) -> Generator[Path, None, None]:
    for file in folder.iterdir():
        if file.suffix.upper() == ".NC":
            yield file

def access_line_4(yield_file: Path) -> str | None:
    with yield_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i == 4:
                return line.rstrip("\n")
    return None

def fix_material_format(text: str) -> str:
    fixed = re.sub(r"\(MA/(\d\.\d{4})[^\s)]*", r"(MA/\1", text)
    if not fixed.endswith(")"):
        fixed += ")"
    return fixed

def write_line_4(file_path: Path, new_line: str) -> None:
    # Přečte celý soubor, přepíše 4. řádek a zapíše zpět
    lines = file_path.read_text(encoding="utf-8").splitlines()
    if len(lines) >= 4:
        lines[3] = new_line
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        cons.log(f"{file_path.name}: Soubor má méně než 4 řádky, nelze upravit.", style="yellow")

if __name__ == "__main__":
    cons.rule()
    nc_files = get_nc_files(folder=CNCFOLDER)
    for nc_file in nc_files:
        line_4 = access_line_4(yield_file=nc_file)
        if line_4:
            if pattern.fullmatch(line_4):
                cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
            else:
                fixed_line = fix_material_format(line_4)
                cons.log(f"{nc_file.name}: {line_4} -> incorrect, opravujem na: {fixed_line}", style="red")
                write_line_4(nc_file, fixed_line)
        else:
            cons.log(f"{nc_file.name}: 4. řádek nenalezen", style="yellow")
    cons.rule()
