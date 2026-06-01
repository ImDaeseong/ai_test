import os
import queue
import string
import subprocess
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


TEXT_EXTENSIONS = {
    ".bat",
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".lua",
    ".md",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".srt",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    "$Recycle.Bin",
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    "System Volume Information",
}

EXTENSION_PRESETS = [
    ("C/C++ (MFC)",  ".h .hpp .cpp .c .rc .def"),
    ("Java",         ".java"),
    ("Kotlin",       ".kt .kts"),
    ("Swift",        ".swift"),
    ("Web",          ".html .js .ts .css .vue .jsx .tsx .php"),
    ("All text",     ""),
]


@dataclass(frozen=True)
class Match:
    path: Path
    line_number: int
    preview: str


class SearchWorker(threading.Thread):
    def __init__(
        self,
        root_path: Path,
        keyword: str,
        case_sensitive: bool,
        include_binary_like: bool,
        extensions: set[str],
        outbox: queue.Queue,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.root_path = root_path
        self.keyword = keyword
        self.case_sensitive = case_sensitive
        self.include_binary_like = include_binary_like
        self.extensions = extensions
        self.outbox = outbox
        self.stop_event = stop_event

    def run(self) -> None:
        checked = 0
        matches = 0

        try:
            for file_path in self._iter_files():
                if self.stop_event.is_set():
                    break

                checked += 1
                if checked % 50 == 0:
                    self.outbox.put(("progress", self.root_path, checked, matches))

                for match in self._find_in_file(file_path):
                    matches += 1
                    self.outbox.put(("match", match))

            status = "cancelled" if self.stop_event.is_set() else "done"
            self.outbox.put((status, self.root_path, checked, matches))
        except Exception as exc:
            self.outbox.put(("error", self.root_path, str(exc)))

    def _iter_files(self):
        for current_root, dirs, files in os.walk(self.root_path, onerror=lambda _error: None):
            dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]

            for file_name in files:
                file_path = Path(current_root) / file_name
                if self._should_read(file_path):
                    yield file_path

    def _should_read(self, file_path: Path) -> bool:
        if self.extensions:
            return file_path.suffix.lower() in self.extensions
        if self.include_binary_like:
            return True
        if file_path.suffix.lower() in TEXT_EXTENSIONS:
            return True
        try:
            with file_path.open("rb") as file:
                sample = file.read(2048)
            return b"\x00" not in sample
        except OSError:
            return False

    def _find_in_file(self, file_path: Path):
        keyword = self.keyword if self.case_sensitive else self.keyword.lower()

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as file:
                for index, line in enumerate(file, start=1):
                    haystack = line if self.case_sensitive else line.lower()
                    if keyword in haystack:
                        yield Match(file_path, index, line.strip())
        except (OSError, UnicodeError):
            return


class FindStringApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Folder String Finder")
        self.geometry("1040x680")
        self.minsize(820, 520)

        self.folder_var = tk.StringVar()
        self.drive_var = tk.StringVar()
        self.all_drives_var = tk.BooleanVar(value=False)
        self.keyword_var = tk.StringVar()
        self.case_sensitive_var = tk.BooleanVar(value=False)
        self.include_binary_like_var = tk.BooleanVar(value=False)
        self.extensions_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select a folder/drive and enter a search string.")

        self.outbox = queue.Queue()
        self.stop_event = threading.Event()
        self.workers: list[SearchWorker] = []
        self.progress_by_root: dict[Path, tuple[int, int]] = {}
        self.matches: list[Match] = []

        self._build_ui()
        self.after(100, self._drain_outbox)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(top, textvariable=self.folder_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(top, text="Browse", command=self._choose_folder).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

        ttk.Label(top, text="Drive").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        drive_controls = ttk.Frame(top)
        drive_controls.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        drive_controls.columnconfigure(0, weight=1)

        drives = self._get_available_drives()
        self.drive_combo = ttk.Combobox(
            drive_controls,
            textvariable=self.drive_var,
            values=[str(path) for path in drives],
            state="readonly",
        )
        self.drive_combo.grid(row=0, column=0, sticky="ew")
        if drives:
            self.drive_var.set(str(drives[0]))

        ttk.Button(drive_controls, text="Use selected drive", command=self._use_selected_drive).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        ttk.Checkbutton(
            drive_controls,
            text="Search all drives",
            variable=self.all_drives_var,
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        ttk.Label(top, text="Search string").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
        )
        keyword_entry = ttk.Entry(top, textvariable=self.keyword_var)
        keyword_entry.grid(row=2, column=1, sticky="ew", pady=(8, 0))
        keyword_entry.bind("<Return>", lambda _event: self._start_search())

        actions = ttk.Frame(top)
        actions.grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Button(actions, text="Search", command=self._start_search).pack(side="left")
        ttk.Button(actions, text="Stop", command=self._stop_search).pack(side="left", padx=(6, 0))

        ttk.Label(top, text="Extensions").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ext_frame = ttk.Frame(top)
        ext_frame.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        ext_frame.columnconfigure(0, weight=1)
        ttk.Entry(ext_frame, textvariable=self.extensions_var).grid(row=0, column=0, sticky="ew")
        self._preset_combo = ttk.Combobox(
            ext_frame,
            values=[name for name, _ in EXTENSION_PRESETS],
            state="readonly",
            width=16,
        )
        self._preset_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._preset_combo.set("프리셋 선택")
        self._preset_combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_preset())

        options = ttk.Frame(top)
        options.grid(row=4, column=1, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(
            options,
            text="Case sensitive",
            variable=self.case_sensitive_var,
        ).pack(side="left")
        ttk.Checkbutton(
            options,
            text="Include binary-like files",
            variable=self.include_binary_like_var,
        ).pack(side="left", padx=(16, 0))

        body = ttk.Frame(self, padding=(12, 0, 12, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        columns = ("path", "line", "preview")
        self.tree = ttk.Treeview(body, columns=columns, show="headings")
        self.tree.heading("path", text="File")
        self.tree.heading("line", text="Line")
        self.tree.heading("preview", text="Preview")
        self.tree.column("path", width=460, anchor="w")
        self.tree.column("line", width=70, anchor="center")
        self.tree.column("preview", width=480, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self._open_selected())

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        bottom = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="Open selected file", command=self._open_selected).grid(
            row=0, column=1, sticky="e"
        )

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory()
        if selected:
            self.folder_var.set(selected)
            self.all_drives_var.set(False)

    def _use_selected_drive(self) -> None:
        selected = self.drive_var.get().strip()
        if selected:
            self.folder_var.set(selected)
            self.all_drives_var.set(False)

    def _get_available_drives(self) -> list[Path]:
        if os.name != "nt":
            return [Path("/")]

        drives = []
        for letter in string.ascii_uppercase:
            path = Path(f"{letter}:\\")
            if path.exists():
                drives.append(path)
        return drives

    def _start_search(self) -> None:
        keyword = self.keyword_var.get()

        if self._search_running():
            messagebox.showinfo("Search in progress", "A search is already running.")
            return
        if not keyword:
            messagebox.showwarning("Search string required", "Enter the string to find.")
            return

        root_paths = self._get_search_roots()
        if not root_paths:
            messagebox.showwarning("Search target required", "Select a folder or drive to search.")
            return

        raw_ext = self.extensions_var.get().strip()
        extensions: set[str] = set()
        if raw_ext:
            for token in raw_ext.replace(",", " ").split():
                ext = token if token.startswith(".") else f".{token}"
                extensions.add(ext.lower())

        self._clear_results()
        self.stop_event.clear()
        self.workers.clear()
        self.progress_by_root.clear()
        self.status_var.set("Searching...")

        for root_path in root_paths:
            worker = SearchWorker(
                root_path=root_path,
                keyword=keyword,
                case_sensitive=self.case_sensitive_var.get(),
                include_binary_like=self.include_binary_like_var.get(),
                extensions=extensions,
                outbox=self.outbox,
                stop_event=self.stop_event,
            )
            self.workers.append(worker)
            worker.start()

    def _apply_preset(self) -> None:
        name = self._preset_combo.get()
        for preset_name, exts in EXTENSION_PRESETS:
            if preset_name == name:
                self.extensions_var.set(exts)
                break

    def _stop_search(self) -> None:
        if self._search_running():
            self.stop_event.set()
            self.status_var.set("Stop requested...")

    def _search_running(self) -> bool:
        return any(worker.is_alive() for worker in self.workers)

    def _get_search_roots(self) -> list[Path]:
        if self.all_drives_var.get():
            return [path for path in self._get_available_drives() if path.is_dir()]

        folder = self.folder_var.get().strip()
        if not folder:
            folder = self.drive_var.get().strip()
        if not folder:
            return []

        root_path = Path(folder)
        if not root_path.is_dir():
            messagebox.showwarning("Invalid folder", "The selected path is not a folder.")
            return []
        return [root_path]

    def _clear_results(self) -> None:
        self.matches.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _drain_outbox(self) -> None:
        for _ in range(200):  # limit per cycle so the tkinter event loop stays responsive
            try:
                message = self.outbox.get_nowait()
            except queue.Empty:
                break

            kind = message[0]
            if kind == "match":
                self._add_match(message[1])
            elif kind == "progress":
                self.progress_by_root[message[1]] = (message[2], message[3])
                self._update_status("Searching")
            elif kind == "done":
                self.progress_by_root[message[1]] = (message[2], message[3])
                label = "Done" if not self._search_running() else "Searching"
                self._update_status(label)
            elif kind == "cancelled":
                self.progress_by_root[message[1]] = (message[2], message[3])
                label = "Cancelled" if not self._search_running() else "Stopping"
                self._update_status(label)
            elif kind == "error":
                self.status_var.set("An error occurred.")
                messagebox.showerror("Error", f"{message[1]}\n{message[2]}")

        self.after(100, self._drain_outbox)

    def _update_status(self, label: str) -> None:
        checked = sum(value[0] for value in self.progress_by_root.values())
        matches = sum(value[1] for value in self.progress_by_root.values())
        roots = len(self.progress_by_root) or len(self.workers)
        self.status_var.set(
            f"{label}: roots {roots}, checked files {checked}, matches {matches}"
        )

    def _add_match(self, match: Match) -> None:
        self.matches.append(match)
        preview = match.preview.replace("\t", " ")
        if len(preview) > 240:
            preview = preview[:237] + "..."
        self.tree.insert("", "end", values=(str(match.path), match.line_number, preview))

    def _open_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        path = values[0]
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))


if __name__ == "__main__":
    app = FindStringApp()
    app.mainloop()
