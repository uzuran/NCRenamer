import os
import threading
import webbrowser

import customtkinter as ctk

from app.burn_table.main import create_view_model as create_burn_view_model
from app.models.formatter_model import FormatterModel
from app.models.material_repository import MaterialRepository
from app.models.settings_model import SettingsModel
from app.models.todo_repository import TodoRepository
from app.services.update_checker import check_for_updates
from app.translations.translations import LANGUAGES
from app.utils.workspace import create_workspace
from app.version import APP_NAME, APP_VERSION
from app.viewmodels.main_view_model import MainViewModel
from app.viewmodels.materials_view_model import MaterialsViewModel
from app.viewmodels.todo_view_model import TodoViewModel
from app.views.add_material_frame import AddMaterialFrame
from app.views.burn_table_frame import BurnTableFrame
from app.views.main_frame import MainFrame
from app.views.materials_frame import MaterialsFrame
from app.views.settings_frame import SettingsFrame
from app.views.todo_frame import TodoFrame


class App(ctk.CTk):
    "Main application class for NCRenamer"

    def __init__(self):
        super().__init__()

        # ── Workspace (must happen first — all paths derive from it) ──────────
        self._workspace, self._username = create_workspace()

        # ── Shared repositories (same file for every Windows login) ───────────
        self.material_repo = MaterialRepository(
            path=self._workspace.materials_path()
        )
        self.todo_repo = TodoRepository(
            path=self._workspace.todo_path()
        )
        self.formatter_model = FormatterModel(self.material_repo)

        # ── Per-user settings ─────────────────────────────────────────────────
        self.settings_model = SettingsModel(
            path=str(self._workspace.user_settings_path(self._username))
        )
        self.settings_model.load()

        self.current_language_code = self.settings_model.settings.get("language", "cs")
        self.texts = LANGUAGES[self.current_language_code]
        self.materials_view_model = MaterialsViewModel(
            app_instance=self,
            repo=self.material_repo,
            texts=self.texts,
        )
        self.todo_view_model = TodoViewModel(
            repo=self.todo_repo,
            texts=self.texts,
        )

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("350x600")

        ctk.set_appearance_mode(
            self.settings_model.settings.get("appearance_mode", "System")
        )

        folder = os.path.dirname(self.settings_model.path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        self.main_frame = MainFrame(
            master=self,
            texts=self.texts,
            app_instance=self,
            viewmodel=None,
        )

        self.main_view_model = MainViewModel(
            formatter_model=self.formatter_model,
        )

        self.main_frame.vm = self.main_view_model
        self.main_frame.pack(fill="both", expand=True)

        self.settings_frame = SettingsFrame(
            master=self,
            app_instance=self,
            app_settings=self.settings_model,
            texts=self.texts,
        )

        self.materials_frame = MaterialsFrame(
            master=self,
            app_instance=self,
            view_model=self.materials_view_model,
            texts=self.texts,
        )

        self.add_material_frame = AddMaterialFrame(
            master=self,
            view_model=self.materials_view_model,
            app_instance=self,
            texts=self.texts,
        )

        # Per-user burn-table VMs — both share the same settings file so the
        # last-opened path is saved once and loaded by either VM on next startup.
        _user_settings_file = self._workspace.user_settings_path(self._username)
        self.vm_steel = create_burn_view_model(
            texts=self.texts,
            sheet_index=0,
            sheet_name="Ocel",
            settings_key="last_table_path",
            settings_file=_user_settings_file,
        )
        self.vm_aluminium = create_burn_view_model(
            texts=self.texts,
            sheet_index=1,
            sheet_name="Hliník",
            settings_key="last_table_path",
            settings_file=_user_settings_file,
        )
        self.vm_steel.set_peer_vm(self.vm_aluminium)
        self.vm_aluminium.set_peer_vm(self.vm_steel)
        self.burn_table_frame = BurnTableFrame(
            master=self,
            app_instance=self,
            vm_steel=self.vm_steel,
            vm_aluminium=self.vm_aluminium,
            texts=self.texts,
        )

        self.todo_frame = TodoFrame(
            master=self,
            view_model=self.todo_view_model,
            app_instance=self,
            texts=self.texts,
        )

        self.show_main_content()
        self._init_burn_tables()

        self._update_check_in_progress = False

        # Global deselect: bind_all fires for every widget in the app regardless
        # of whether CTk frames propagate the event up to the root window.
        self.bind_all("<Button-1>", self._on_global_click, add="+")

        # update check po startu aplikace
        self.after(2000, self.start_update_check)

    def _init_burn_tables(self) -> None:
        """Load or create the per-user burn-table workbook on startup.

        The path is always ``users/<username>/burn_table.xlsx`` inside the
        workspace root, so it is deterministic — no settings-file lookup
        needed.  Both VM sheets (Steel and Aluminium) share the same file.

        Load order:
          1. vm_steel.load_table() / create_new_table() — writes the "Ocel"
             sheet and saves the path to the user settings file.
          2. vm_aluminium.load_table() — ``ensure_sheet_exists`` creates the
             "Hliník" sheet on the same file if it is not present yet.
        """
        path = self._workspace.user_burn_table_path(self._username)
        if path.is_file():
            self.vm_steel.load_table(path)
        else:
            self.vm_steel.create_new_table(path)
        self.vm_aluminium.load_table(path)

    def set_language(self, lang_code: str):
        if self.current_language_code != lang_code:
            self.current_language_code = lang_code
            self.texts = LANGUAGES[lang_code]
            self.settings_model.set("language", lang_code)
            self.settings_model.save()

            self.title(self.texts.get("app_title", "NC Renamer"))
            self.materials_view_model.update_texts(self.texts)
            self.todo_view_model.update_texts(self.texts)
            self.vm_steel.update_texts(self.texts)
            self.vm_aluminium.update_texts(self.texts)
            self.main_frame.update_texts(self.texts)
            self.settings_frame.update_texts(self.texts)
            self.materials_frame.update_texts(self.texts)
            self.add_material_frame.update_texts(self.texts)
            self.burn_table_frame.update_texts(self.texts)
            self.todo_frame.update_texts(self.texts)

    def show_main_content(self):
        self._hide_all_frames()
        self.geometry("350x600")
        self.main_frame.pack(fill="both", expand=True)

    def show_burn_table_content(self):
        self._hide_all_frames()
        self.geometry("1100x650")
        self.burn_table_frame.pack(fill="both", expand=True)

    def show_settings_content(self):
        self._hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)

    def show_materials_content(self):
        self._hide_all_frames()
        # get loaded CSV directly
        processed_content = self.materials_view_model.get_materials()
        self.materials_frame.update_treeview_display(processed_content)
        self.materials_frame.pack(fill="both", expand=True)

    def show_add_materials_content(self):
        self._hide_all_frames()
        self.add_material_frame.pack(fill="both", expand=True)

    def show_todo_content(self):
        self._hide_all_frames()
        self.geometry("530x600")
        self.todo_frame.update_treeview()
        self.todo_frame.pack(fill="both", expand=True)

    def _is_inside_interactive(self, widget) -> bool:
        """Walk up the parent chain; return True if any ancestor is an interactive widget."""
        _ctk_interactive = (
            ctk.CTkEntry,
            ctk.CTkButton,
            ctk.CTkTextbox,
            ctk.CTkComboBox,
            ctk.CTkOptionMenu,
        )
        _tk_interactive_classes = {
            "TScrollbar",
            "Scrollbar",
            "TCombobox",
            "Combobox",
            "TButton",
            "Button",
        }
        current = widget
        while current is not None:
            if isinstance(current, _ctk_interactive):
                return True
            if current.winfo_class() in _tk_interactive_classes:
                return True
            parent_name = current.winfo_parent()
            if not parent_name:
                break
            try:
                current = self.nametowidget(parent_name)
            except Exception:
                break
        return False

    def _on_global_click(self, event) -> None:
        widget = event.widget

        # event.widget can be a raw Tk path string when the widget is destroyed
        # before the event fires (common with bind_all + CTk internal callbacks).
        if isinstance(widget, str):
            return

        # Clicks inside a popup / dialog belong to that window — ignore.
        if widget.winfo_toplevel() is not self:
            return

        # Walk up widget ancestors: any interactive CTk or ttk control → preserve.
        if self._is_inside_interactive(widget):
            return

        cls = widget.winfo_class()

        # Treeview: only clear if the click hit empty space (no row under cursor).
        if cls == "Treeview":
            if not widget.identify_row(event.y):
                widget.selection_remove(widget.selection())
                widget.focus("")
            return

        # Background frame or root window → clear every TreeView in the app.
        cleared = False
        for tree in (
            self.materials_frame.tree,
            self.add_material_frame.tree,
            self.burn_table_frame.steel_tab.tree,
            self.burn_table_frame.alu_tab.tree,
            self.todo_frame.tree,
        ):
            selected = tree.selection()
            if selected:
                tree.selection_remove(selected)
                tree.focus("")
                cleared = True
        if cleared:
            self.focus_set()

    def _hide_all_frames(self):
        for frame in (
            self.main_frame,
            self.settings_frame,
            self.materials_frame,
            self.add_material_frame,
            self.burn_table_frame,
            self.todo_frame,
        ):
            frame.pack_forget()

    def start_update_check(self):
        if self._update_check_in_progress:
            return

        self._update_check_in_progress = True
        threading.Thread(target=self.check_updates, daemon=True).start()

    def check_updates(self):
        try:
            update_available, url = check_for_updates()
        except Exception:
            update_available, url = False, None
        finally:
            self.after(0, self._finish_update_check, update_available, url)

    def _finish_update_check(self, update_available, url):
        self._update_check_in_progress = False
        if update_available:
            webbrowser.open(url)


if __name__ == "__main__":
    app = App()
    app.mainloop()
