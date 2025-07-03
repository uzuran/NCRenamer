"""Main code"""

import re
import sys
from pathlib import Path
from rich.console import Console


class NcFormatter:
    PATTERN: re.Pattern[str] = re.compile(
        r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěšřžýáíéůúťň]+)?\)?"
    )

    def __init__(self):
        self.pattern = self.PATTERN
        self.cons = Console()

    def get_nc_files(self, file_path: Path) -> list[Path]:
        """
        Vrací seznam všech .NC souborů v adresáři.
        Pokud adresář neexistuje, vypíše chybu a ukončí program.
        """
        if not file_path.exists() or not file_path.is_dir():
            self.cons.log(
                f"Adresář {file_path} neexistuje nebo není adresář.", style="red"
            )
            sys.exit(1)

        return [file for file in file_path.iterdir() if file.suffix.upper() == ".NC"]

    def access_line_4(self, nc_file: Path) -> str | None:
        """Načte 4. řádek souboru, nebo vrátí None pokud neexistuje"""
        with nc_file.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if i == 4:
                    return line.rstrip("\n")
        return None

    def fix_material_format(self, text: str) -> str | None:
        """
        Vrátí první validní výskyt typu (MA/číslo) nebo (MA/číslo název)
        Oprava odstraní nevalidní části jako pomlčky nebo špatné znaky.
        """

        match = re.search(r"MA/(\d\.\d{4})(?: ?[a-zA-Zčěšřžýáíéůúťň]+)?", text)
        if match:
            return f"({match.group(0)})"
        return None

    def write_line_4(self, file_path: Path, new_line: str) -> None:
        """Přepíše 4. řádek souboru novým textem, pokud má soubor alespoň 4 řádky"""
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if len(lines) >= 4:
            lines[3] = new_line
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            self.cons.log(
                f"{file_path.name}: Soubor má méně než 4 řádky, nelze upravit.",
                style="yellow",
            )

    def process_file(self, nc_file: Path) -> bool:
        """
        Zpracuje jeden NC soubor - ověří a případně opraví 4. řádek.
        Vrací True pokud došlo ke změně, jinak False.
        """
        line_4 = self.access_line_4(nc_file)
        if line_4 is None:
            self.cons.log(f"{nc_file.name}: 4. řádek nenalezen", style="yellow")
            return False

        if self.pattern.fullmatch(line_4):
            self.cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
            return False

        fixed_line = self.fix_material_format(line_4)
        if fixed_line:
            self.cons.log(
                f"{nc_file.name}: {line_4} -> opraveno na: {fixed_line}", style="red"
            )
            self.write_line_4(nc_file, fixed_line)
            return True
        else:
            self.cons.log(
                f"{nc_file.name}: {line_4} -> incorrect, ale nelze opravit",
                style="bold red",
            )
            return False
