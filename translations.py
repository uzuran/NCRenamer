# translations.py

# Slovník pro češtinu
cs = {
    "app_title": "NCRenamer",
    "select_nc_files": "Vyberte NC soubory",
    "rename_nc_files": "Přejmenovat NC soubory",
    "report_bug": "Nahlásit chybu",
    "renamed_ncs": "Přejmenované NC soubory",
    "selected_files": "Vybráno: {} souborů",
    "processed_history": "Historie zpracovaných materiálů:",
    "search_placeholder": "Zadejte hledaný výraz...",
    "search_button": "Hledat",
    "back_button": "Zpět",
    "appearance_mode_setting": "Změnit režim vzhledu",
    "language_setting": "Zvolit jazyk",
    "email_count": "Počet hlášení chyb: {}",
    "done_title": "Hotovo",
    "done_message": "Zpracování dokončeno.\nCelkem souborů: {}",
    "no_files_to_rename": "Žádné soubory k přejmenování.",
    "file_modified": "✅ Upraveno: {}",
    "file_no_change": "✔️ Bez změny: {}",
    "reset_counter_title": "Počítadlo resetováno",
    "reset_counter_message": "Počítadlo hlášení chyb bylo resetováno na 0.",
    "email_error_title": "Chyba",
    "email_error_message": "Nepodařilo se otevřít výchozí e-mailový klient. Ujistěte se, že máte nějaký nastavený.",
    "password_prompt": "Zadejte heslo pro resetování počítadla.",
    "password_incorrect": "Nesprávné heslo!",
}

# Slovník pro angličtinu
en = {
    "app_title": "NCRenamer",
    "select_nc_files": "Select NC files",
    "rename_nc_files": "Rename NC files",
    "report_bug": "Report Bug",
    "renamed_ncs": "Renamed NC files",
    "selected_files": "Selected: {} files",
    "processed_history": "History of Processed Materials:",
    "search_placeholder": "Enter search term...",
    "search_button": "Search",
    "back_button": "Back",
    "appearance_mode_setting": "Change Appearance Mode",
    "language_setting": "Select Language",
    "email_count": "Number of bug reports: {}",
    "done_title": "Done",
    "done_message": "Processing complete.\nTotal files: {}",
    "no_files_to_rename": "No files to rename.",
    "file_modified": "✅ Modified: {}",
    "file_no_change": "✔️ No change: {}",
    "reset_counter_title": "Counter Reset",
    "reset_counter_message": "Bug report counter has been reset to 0.",
    "email_error_title": "Error",
    "email_error_message": "Could not open default email client. Make sure one is configured.",
    "password_prompt": "Enter password to reset counter.",
    "password_incorrect": "Incorrect password!",
}

# Hlavní slovník, který obsahuje všechny jazyky
LANGUAGES = {
    "cs": cs,
    "en": en,
}

# Mapování zobrazených názvů jazyků na kódy jazyků
LANGUAGE_NAMES = {
    "Čeština": "cs",
    "English": "en",
}
