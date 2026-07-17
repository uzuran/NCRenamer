"""part_storage_frame.py — Leftover parts storage UI.

Image pipeline architecture
───────────────────────────
MAIN THREAD only:
  • clipboard read (ImageGrab.grabclipboard)
  • overwrite confirm dialog (messagebox)
  • token generation and preview-cache management
  • CTkImage creation
  • label.configure()
  • self.after()
  • treeview updates

WORKER THREAD only:
  • vm.save_image_no_notify() → PNG save to disk
  • PIL thumbnail resize
  • queue.SimpleQueue.put((token, part_id, pil_img))

Worker NEVER calls: after(), CTkImage, configure(), messagebox, notify(), treeview.

Paste flow (main thread → worker → main thread):
  1  Main: grab clipboard → PIL.Image
  2  Main: confirm overwrite if image_path already exists
  3  Main: pop cache entry, configure label to "…", new token, awaiting=True
  4  Main: threading.Thread(target=_save_worker).start()
  5  Main: self.after(0, self._drain_queue)        ← only after() from main thread
  6  Worker: save_image_no_notify() + thumb resize + queue.put()
  7  Main drain: CTkImage(pil_img), label.configure(image=…), cache[part_id]=ctk_img
"""

from __future__ import annotations

import queue
import threading
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from app.viewmodels.part_storage_view_model import PartStorageViewModel

_THUMB_SIZE = (174, 174)
_DRAIN_POLL_MS = 20


# ── Worker function (module-level, zero Tkinter surface) ─────────────────────

def _save_worker(
    token: object,
    part_id: str,
    pil_img,
    vm,
    result_q: queue.SimpleQueue,
) -> None:
    """Save PNG and produce a thumbnail.  Called on a daemon thread.

    Contract:
    • NEVER calls any Tkinter API, CTkImage, after(), configure(), or notify().
    • Only calls: vm.save_image_no_notify(), PIL operations, queue.put().
    """
    saved = vm.save_image_no_notify(part_id, pil_img)
    if not saved:
        result_q.put((token, part_id, None))
        return
    try:
        thumb = pil_img.copy()
        thumb.thumbnail(_THUMB_SIZE)
    except Exception:
        thumb = None
    result_q.put((token, part_id, thumb))


# ── Frame ─────────────────────────────────────────────────────────────────────

class PartStorageFrame(ctk.CTkFrame):
    """Add, edit, delete, search, and preview leftover parts from laser cutting."""

    def __init__(
        self,
        master=None,
        view_model: PartStorageViewModel | None = None,
        app_instance=None,
        texts: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.vm = view_model
        self.app_instance = app_instance
        self.texts = texts or {}
        self._editing_id: str | None = None

        # ── Image pipeline state (all mutated on main thread only) ───────────
        self._preview_cache: dict[str, ctk.CTkImage] = {}
        self._thumb_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._thumb_token: object = object()
        self._thumb_awaiting: bool = False
        self._thumbnail_ref = None          # hard ref → prevents CTkImage GC

        # Rebuild guard: suppresses _reset_edit_state during tree.delete()
        self._rebuilding: bool = False

        self._build()
        if self.vm is not None:
            self.vm.set_confirm_duplicate(self._make_confirm_duplicate())
            self.vm.subscribe(self.reload_treeview)

    # ─── Build ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.title_lbl = ctk.CTkLabel(
            self,
            text=self.texts.get("part_storage", "Leftovers"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title_lbl.pack(pady=(6, 2))

        fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        fields_frame.pack(pady=(0, 2))

        self.search_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_search_label", "Hledat:"),
            width=110,
            anchor="e",
        )
        self.search_lbl.grid(row=0, column=0, padx=(0, 6), pady=1, sticky="e")
        self.search_entry = ctk.CTkEntry(
            fields_frame,
            placeholder_text=self.texts.get(
                "part_search_placeholder", "Search part number…"
            ),
            width=230,
        )
        self.search_entry.grid(row=0, column=1, pady=1, sticky="w")
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_treeview())

        self.number_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_number_prompt", "Part number:"),
            width=110,
            anchor="e",
        )
        self.number_lbl.grid(row=1, column=0, padx=(0, 6), pady=1, sticky="e")
        self.number_entry = ctk.CTkEntry(fields_frame, width=230)
        self.number_entry.grid(row=1, column=1, pady=1, sticky="w")

        self.location_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_location_prompt", "Location:"),
            width=110,
            anchor="e",
        )
        self.location_lbl.grid(row=2, column=0, padx=(0, 6), pady=1, sticky="e")
        self.location_entry = ctk.CTkEntry(fields_frame, width=230)
        self.location_entry.grid(row=2, column=1, pady=1, sticky="w")

        self.notes_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_notes_prompt", "Notes:"),
            width=110,
            anchor="e",
        )
        self.notes_lbl.grid(row=3, column=0, padx=(0, 6), pady=1, sticky="e")
        self.notes_entry = ctk.CTkEntry(fields_frame, width=230)
        self.notes_entry.grid(row=3, column=1, pady=1, sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 2))

        self.add_btn = ctk.CTkButton(
            btn_frame,
            text=self.texts.get("part_add", "Add"),
            width=100,
            command=self._cmd_add,
        )
        self.add_btn.pack(side="left", padx=5)

        self.update_btn = ctk.CTkButton(
            btn_frame,
            text=self.texts.get("part_update", "Update"),
            width=100,
            state="disabled",
            command=self._cmd_update,
        )
        self.update_btn.pack(side="left", padx=5)

        self.delete_btn = ctk.CTkButton(
            btn_frame,
            text=self.texts.get("part_delete", "Delete"),
            width=100,
            fg_color="#922b21",
            hover_color="#6e1f18",
            command=self._cmd_delete,
        )
        self.delete_btn.pack(side="left", padx=5)

        flash_frame = ctk.CTkFrame(self, fg_color="transparent")
        flash_frame.pack(pady=(0, 2))
        self.flash_lbl = ctk.CTkLabel(flash_frame, text="")
        self.flash_lbl.pack()

        # ── Main content: treeview (left) + thumbnail panel (right) ──────────
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        # Left: treeview
        tree_frame = ctk.CTkFrame(content_frame)
        tree_frame.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("part_number", "location", "date_added", "notes"),
            show="headings",
        )
        self.tree.heading(
            "part_number", text=self.texts.get("part_col_number", "Part Number")
        )
        self.tree.heading(
            "location", text=self.texts.get("part_col_location", "Location")
        )
        self.tree.heading(
            "date_added", text=self.texts.get("part_col_date", "Date Added")
        )
        self.tree.heading(
            "notes", text=self.texts.get("part_col_notes", "Notes")
        )
        self.tree.column("part_number", width=130, minwidth=80, anchor="w", stretch=False)
        self.tree.column("location",    width=130, minwidth=80, anchor="w", stretch=False)
        self.tree.column("date_added",  width=100, minwidth=80, anchor="center", stretch=False)
        self.tree.column("notes",       width=180, minwidth=80, anchor="w", stretch=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>",         self._on_tree_click)
        self.tree.bind("<Escape>",           lambda e: self._deselect())
        self.tree.bind("<Control-v>",        lambda e: self._paste_image())

        # Right: thumbnail panel
        self._build_image_panel(content_frame)

        self.back_btn = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            command=self._go_back,
        )
        self.back_btn.pack(pady=10, padx=25, fill="x")

        self.update_treeview()

    def _build_image_panel(self, parent) -> None:
        """Build the right-side thumbnail panel."""
        panel = ctk.CTkFrame(parent, width=190)
        panel.pack(side="right", fill="y", padx=(6, 0))
        panel.pack_propagate(False)

        ctk.CTkLabel(
            panel,
            text=self.texts.get("part_image_label", "Screenshot:"),
            font=ctk.CTkFont(size=12),
        ).pack(pady=(8, 2))

        # Thumbnail display area
        thumb_bg = ctk.CTkFrame(panel, width=182, height=182, fg_color="#1a1a1a")
        thumb_bg.pack(pady=(0, 6))
        thumb_bg.pack_propagate(False)

        self.thumbnail_lbl = ctk.CTkLabel(
            thumb_bg,
            text=self.texts.get("part_no_image_placeholder", "No image"),
            image=None,
            width=182,
            height=182,
        )
        self.thumbnail_lbl.pack(expand=True)
        self.thumbnail_lbl.bind("<Control-v>", lambda e: self._paste_image())
        self.thumbnail_lbl.bind("<Button-1>", lambda _: self._open_original_image())

        self.paste_btn = ctk.CTkButton(
            panel,
            text=self.texts.get("part_paste_image", "Paste (Ctrl+V)"),
            width=170,
            command=self._paste_image,
        )
        self.paste_btn.pack(pady=(0, 4))

        self.remove_img_btn = ctk.CTkButton(
            panel,
            text=self.texts.get("part_remove_image", "Remove image"),
            width=170,
            fg_color="#922b21",
            hover_color="#6e1f18",
            command=self._remove_image,
        )
        self.remove_img_btn.pack(pady=(0, 4))

    # ─── Treeview helpers ─────────────────────────────────────────────────────

    def reload_treeview(self) -> None:
        self.update_treeview()

    def update_treeview(self) -> None:
        """Reload treeview and restore the previous selection."""
        query = self.search_entry.get() if hasattr(self, "search_entry") else ""
        last_id = self._editing_id

        self._rebuilding = True
        try:
            self.tree.delete(*self.tree.get_children())
            if self.vm is None:
                return
            for item in self.vm.get_all_parts(query):
                raw_date = item.get("date_added", "")
                try:
                    y, m, d = raw_date.split("-")
                    date_str = f"{d}.{m}.{y}"
                except Exception:
                    date_str = raw_date or "—"
                self.tree.insert(
                    "",
                    "end",
                    iid=item["id"],
                    values=(
                        item.get("part_number", ""),
                        item.get("location", ""),
                        date_str,
                        item.get("notes", ""),
                    ),
                )
        finally:
            self._rebuilding = False

        if last_id and self.tree.exists(last_id):
            self.tree.selection_set(last_id)
            self.tree.see(last_id)
            self._editing_id = last_id
        else:
            self._editing_id = None
            self._update_thumbnail(None)

    # ─── Selection handling ───────────────────────────────────────────────────

    def _on_tree_select(self, event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            self._reset_edit_state()
            return
        self._editing_id = selected[0]
        values = self.tree.item(self._editing_id, "values")
        self.number_entry.delete(0, "end")
        self.number_entry.insert(0, values[0] if len(values) > 0 else "")
        self.location_entry.delete(0, "end")
        self.location_entry.insert(0, values[1] if len(values) > 1 else "")
        self.notes_entry.delete(0, "end")
        self.notes_entry.insert(0, values[3] if len(values) > 3 else "")
        self.update_btn.configure(state="normal")
        self.add_btn.configure(state="disabled")
        self._update_thumbnail(self._editing_id)

    def _reset_edit_state(self) -> None:
        if self._rebuilding:
            return
        self._editing_id = None
        self.number_entry.delete(0, "end")
        self.location_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.update_btn.configure(state="disabled")
        self.add_btn.configure(state="normal")
        self._thumb_token = object()   # cancel any in-flight worker
        self._thumb_awaiting = False
        self._clear_thumbnail()

    def _deselect(self) -> None:
        for iid in self.tree.selection():
            self.tree.selection_remove(iid)

    def _on_tree_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if not row or row in self.tree.selection():
            self._deselect()

    # ─── Thumbnail pipeline (main-thread side) ────────────────────────────────

    def _clear_thumbnail(self) -> None:
        """Hard-clear thumbnail_lbl so no ghost image remains.

        configure(image=None) alone is insufficient: CTkLabel stores the
        PhotoImage on its internal _label.image attribute to prevent GC, and
        does not clear that attribute when image=None is passed.  Clearing it
        directly ensures Tkinter actually drops the reference and the old image
        cannot bleed through behind the "No image" text.
        """
        if not hasattr(self, "thumbnail_lbl"):
            return
        placeholder = self.texts.get("part_no_image_placeholder", "No image")
        self.thumbnail_lbl.configure(image=None, text=placeholder)
        self.thumbnail_lbl.image = None
        self._thumbnail_ref = None
        # Belt-and-suspenders: clear the internal tk.Label reference kept by
        # CTkLabel so the old PhotoImage is fully released.
        for _attr in ("_label", "_text_label"):
            _inner = getattr(self.thumbnail_lbl, _attr, None)
            if _inner is not None:
                try:
                    _inner.configure(image="")
                    _inner.image = None
                except Exception:
                    pass

    def _release_image_ref(self) -> None:
        """Disconnect CTkLabel's internal tk.Label image ref before releasing old CTkImage.

        CTkLabel's inner tk.Label holds the Tk *name string* of the current
        PhotoImage (e.g. "pyimage3"), not the Python object.  When we set
        self._thumbnail_ref = None the Python CTkImage may be garbage-collected,
        and CTkImage.__del__() deletes that name from Tk's registry.  If the
        tk.Label widget still has the now-invalid name configured, the next Tk
        redraw (triggered by a frame switch, resize, or DPI change) silently
        fails and the entire window goes black.  Calling this first tells Tk to
        stop using the old name before the underlying resource is freed.
        """
        if not hasattr(self, "thumbnail_lbl"):
            return
        for _attr in ("_label", "_text_label"):
            _inner = getattr(self.thumbnail_lbl, _attr, None)
            if _inner is not None:
                try:
                    _inner.configure(image="")
                    _inner.image = None
                except Exception:
                    pass

    def _update_thumbnail(self, part_id: str | None) -> None:
        """Show thumbnail for *part_id*.  Always runs on the main thread.

        Cache hit  → instant (no I/O, no thread).
        Cache miss → show "…", start worker, schedule drain.
        part_id is None → show placeholder text.
        """
        # Cancel any in-flight worker by advancing the token.
        self._thumb_token = token = object()
        self._thumb_awaiting = False
        self._release_image_ref()
        self._thumbnail_ref = None

        if not hasattr(self, "thumbnail_lbl"):
            return

        if part_id is None or self.vm is None:
            self._clear_thumbnail()
            return

        # ── Cache hit: zero I/O, zero threads ────────────────────────────────
        if part_id in self._preview_cache:
            ctk_img = self._preview_cache[part_id]
            self.thumbnail_lbl.configure(image=ctk_img, text="")
            self._thumbnail_ref = ctk_img
            return

        # ── Check whether an image file exists ───────────────────────────────
        img_path = self.vm.get_image_path(part_id)
        if img_path is None:
            self._clear_thumbnail()
            return

        # ── Cache miss: start background loader ───────────────────────────────
        self.thumbnail_lbl.configure(image=None, text="…")
        self._thumb_awaiting = True

        def _load_worker() -> None:
            try:
                from PIL import Image  # noqa: PLC0415
                img = Image.open(str(img_path))
                img.load()
                img.thumbnail(_THUMB_SIZE)
            except Exception:
                img = None
            self._thumb_queue.put((token, part_id, img))

        threading.Thread(target=_load_worker, daemon=True).start()
        self.after(0, self._drain_queue)

    def _paste_image(self) -> None:
        """Handle Ctrl+V: grab clipboard, confirm overwrite, save in background.

        Steps 1-5 run on the MAIN THREAD.
        Step 6 runs on a DAEMON THREAD.
        Steps 7-9 run back on the MAIN THREAD via _drain_queue().
        """
        if not self._editing_id or self.vm is None:
            self._show_flash(
                self.texts.get("part_no_selected", "No part selected."), "red"
            )
            return

        # ── Step 1: grab clipboard (Windows clipboard API — main thread only) ─
        try:
            from PIL import Image, ImageGrab  # noqa: PLC0415
            clip_img = ImageGrab.grabclipboard()
            if not isinstance(clip_img, Image.Image):
                self._show_flash(
                    self.texts.get("part_no_clipboard_image", "No image in clipboard."),
                    "red",
                )
                return
        except Exception:
            self._show_flash(self.texts.get("part_image_error", "Image error."), "red")
            return

        part_id = self._editing_id

        # ── Step 2: confirm overwrite on the main thread ──────────────────────
        if self.vm.get_image_path(part_id) is not None:
            confirmed = messagebox.askyesno(
                title=self.texts.get("part_image_replace_title", "Replace image?"),
                message=self.texts.get(
                    "part_image_replace_confirm",
                    "Part already has an image. Replace it?",
                ),
                parent=self,
            )
            if not confirmed:
                self._show_flash(
                    self.texts.get("part_image_cancelled", "Cancelled."), "red"
                )
                return

        # ── Step 3: update UI state on the main thread ────────────────────────
        self._preview_cache.pop(part_id, None)       # evict stale cache entry
        self._release_image_ref()                     # disconnect Tk ref before GC
        self._thumbnail_ref = None                    # release old CTkImage ref
        self._thumb_token = token = object()          # new token for this paste
        self._thumb_awaiting = True
        self.thumbnail_lbl.configure(image=None, text="…")

        # ── Step 4: detach a private copy so the worker owns it exclusively ───
        clip_copy = clip_img.copy()

        # ── Step 5: start daemon thread (save + resize only, NO Tkinter) ──────
        threading.Thread(
            target=_save_worker,
            args=(token, part_id, clip_copy, self.vm, self._thumb_queue),
            daemon=True,
        ).start()

        # ── Step 6: schedule drain from the MAIN thread (never from worker) ───
        self.after(0, self._drain_queue)
        # Fallback: if the drain result was stale (token superseded while the
        # confirm dialog ran its nested event loop), reload from disk.
        # Guard: skip if the user navigated away OR drain already cached it —
        # without the guard, _update_thumbnail() advances the token and
        # cancels any in-flight load for the newly selected part.
        self.after(
            200,
            lambda pid=part_id, t=token: (
                self._update_thumbnail(pid)
                if self._editing_id == pid
                and pid not in self._preview_cache
                and t is self._thumb_token
                else None
            ),
        )

        self._show_flash(
            self.texts.get("part_image_saved", "Image saved."), "green"
        )

    def _drain_queue(self) -> None:
        """Consume all queued worker results.  Always runs on the main thread.

        For each result whose token matches the current token:
        • create CTkImage
        • configure label
        • store in preview cache

        Reschedules itself every 20 ms while a worker is still in-flight.
        self.after() is ONLY called here — never from the worker thread.
        """
        if not hasattr(self, "thumbnail_lbl"):
            return

        while True:
            try:
                tok, part_id, pil_img = self._thumb_queue.get_nowait()
            except queue.Empty:
                break

            if tok is not self._thumb_token:
                continue  # stale result from a superseded paste — discard

            self._thumb_awaiting = False

            if pil_img is None:
                self.thumbnail_lbl.configure(
                    image=None,
                    text=self.texts.get("part_image_error", "Error"),
                )
            else:
                try:
                    self._release_image_ref()
                    self._thumbnail_ref = None
                    ctk_img = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=(pil_img.width, pil_img.height),
                    )
                    self.thumbnail_lbl.configure(image=ctk_img, text="")
                    self._thumbnail_ref = ctk_img          # keep alive (GC guard)
                    if part_id:
                        self._preview_cache[part_id] = ctk_img
                except Exception:
                    self.thumbnail_lbl.configure(
                        image=None,
                        text=self.texts.get("part_image_error", "Error"),
                    )

        if self._thumb_awaiting:
            self.after(_DRAIN_POLL_MS, self._drain_queue)

    def _remove_image(self) -> None:
        """Remove the image for the currently selected part."""
        if not self._editing_id or self.vm is None:
            self._show_flash(
                self.texts.get("part_no_selected", "No part selected."), "red"
            )
            return
        part_id = self._editing_id
        ok, msg = self.vm.remove_image(part_id)
        if ok:
            self._preview_cache.pop(part_id, None)
            self._thumbnail_ref = None
            self._update_thumbnail(None)
        self._show_flash(msg, "green" if ok else "red")

    def _open_original_image(self) -> None:
        """Open the full-size image in the OS default viewer."""
        if not self._editing_id or self.vm is None:
            return
        img_path = self.vm.get_image_path(self._editing_id)
        if not img_path:
            return
        try:
            import os
            import subprocess
            import sys
            if sys.platform == "win32":
                os.startfile(str(img_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(img_path)])
            else:
                subprocess.Popen(["xdg-open", str(img_path)])
        except Exception:
            pass

    # ─── CRUD commands ────────────────────────────────────────────────────────

    def _cmd_add(self) -> None:
        if self.vm is None:
            return
        success, msg = self.vm.add_part(
            self.number_entry.get(),
            self.location_entry.get(),
            self.notes_entry.get(),
        )
        if success:
            self._reset_edit_state()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_update(self) -> None:
        if not self._editing_id or self.vm is None:
            return
        success, msg = self.vm.update_part(
            self._editing_id,
            self.number_entry.get(),
            self.location_entry.get(),
            self.notes_entry.get(),
        )
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_delete(self) -> None:
        selected = self.tree.selection()
        if not selected or self.vm is None:
            self._show_flash(
                self.texts.get("part_no_selected", "No part selected."), "red"
            )
            return
        part_id = selected[0]
        self._preview_cache.pop(part_id, None)      # clear cache before delete
        success, msg = self.vm.delete_part(part_id)
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _make_confirm_duplicate(self):
        def confirm(part_number: str) -> bool:
            msg = self.texts.get(
                "part_exists_confirm",
                "Part number {} already exists. Add anyway?",
            ).format(part_number)
            return messagebox.askyesno(
                title=self.texts.get("part_exists_title", "Duplicate part"),
                message=msg,
                parent=self,
            )
        return confirm

    def _show_flash(self, message: str, color: str = "green") -> None:
        self.flash_lbl.configure(text=message, text_color=color)
        self.after(2500, lambda: self.flash_lbl.configure(text=""))

    def _go_back(self) -> None:
        if self.app_instance:
            self.app_instance.show_main_content()

    # ─── Language switch ──────────────────────────────────────────────────────

    def update_texts(self, new_texts: dict) -> None:
        self.texts = new_texts
        self.title_lbl.configure(text=new_texts.get("part_storage", "Leftovers"))
        self.search_lbl.configure(text=new_texts.get("part_search_label", "Hledat:"))
        self.search_entry.configure(
            placeholder_text=new_texts.get(
                "part_search_placeholder", "Search part number…"
            )
        )
        self.number_lbl.configure(
            text=new_texts.get("part_number_prompt", "Part number:")
        )
        self.location_lbl.configure(
            text=new_texts.get("part_location_prompt", "Location:")
        )
        self.notes_lbl.configure(text=new_texts.get("part_notes_prompt", "Notes:"))
        self.add_btn.configure(text=new_texts.get("part_add", "Add"))
        self.update_btn.configure(text=new_texts.get("part_update", "Update"))
        self.delete_btn.configure(text=new_texts.get("part_delete", "Delete"))
        self.back_btn.configure(text=new_texts.get("back_button", "Back"))
        self.tree.heading(
            "part_number", text=new_texts.get("part_col_number", "Part Number")
        )
        self.tree.heading(
            "location", text=new_texts.get("part_col_location", "Location")
        )
        self.tree.heading(
            "date_added", text=new_texts.get("part_col_date", "Date Added")
        )
        self.tree.heading(
            "notes", text=new_texts.get("part_col_notes", "Notes")
        )
