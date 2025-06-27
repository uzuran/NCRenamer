"""Main file"""

from pathlib import Path
import sys
import re
from typing import Generator
from rich.console import Console

# ---
cons: Console = Console()

CNCFOLDER: Path = Path("./CNCs")
pattern = re.compile(r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?\)?")

if not CNCFOLDER.exists() or not CNCFOLDER.is_dir():
    cons.log(f"adresar: {CNCFOLDER} neexistuje, koncim program!", style="red")
    sys.exit()


def get_nc_files(folder: Path) -> Generator[Path, None, None]:
    """Generuje postupne soubor po souboru"""
    for file in folder.iterdir():
        if file.suffix.upper() == ".NC":
            yield file


def access_line_4(yield_file: Path) -> str | None:
    """ziskame radek 4"""
    with yield_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i == 4:
                return line.strip()
    return None


if __name__ == "__main__":
    cons.rule()
    nc_files = get_nc_files(folder=CNCFOLDER)
    for nc_file in nc_files:
        line_4 = access_line_4(yield_file=nc_file)
        if line_4:
            # Ověření regexem
            if pattern.fullmatch(line_4):
                cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
            else:
                cons.log(f"{nc_file.name}: {line_4} -> incorrect", style="red")
        else:
            cons.log(f"{nc_file.name}: 4. řádek nenalezen", style="yellow")
    cons.rule()
