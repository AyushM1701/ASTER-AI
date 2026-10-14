"""AsterSetup; trust root is compiled in, not supplied by the download server."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from aster_release.installer import authenticated_bytes, authenticated_distribution, install


def main():
    import tkinter as tk
    from tkinter import filedialog
    # PyInstaller bundles the exact generated trust file. No command-line URL overrides.
    trust_path = Path(sys._MEIPASS) / "installer-trust.json" if getattr(sys, "frozen", False) else Path(os.environ["ASTER_BUILD_TRUST_FILE"])
    trust = json.loads(trust_path.read_text(encoding="utf-8"))
    ui = tk.Tk()
    ui.title("Install Aster")
    ui.geometry("600x350")
    ui.configure(bg="#0d141a")
    tk.Label(ui, text="Aster setup", bg="#0d141a", fg="#79d9c6", font=("Segoe UI", 22)).pack(anchor="w", padx=24, pady=20)
    label = tk.Label(ui, text="Choose where to install Aster. Initial setup needs an internet connection.\nOnce installed, Aster runs locally and offline.", justify="left", wraplength=540, bg="#0d141a", fg="#d7e0e6", font=("Segoe UI", 11))
    label.pack(anchor="w", padx=24)
    directory = tk.StringVar(value=str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Aster"))
    tk.Entry(ui, textvariable=directory, width=72).pack(padx=24, pady=12)
    tk.Button(ui, text="Choose folder", command=lambda: directory.set(filedialog.askdirectory() or directory.get())).pack(anchor="w", padx=24)
    messages, stop = queue.Queue(), threading.Event()
    worker = None
    offline = None
    installed = None
    def perform(root, offline_parts):
        try:
            messages.put(("status", "Checking authenticated release metadata…"))
            if offline_parts:
                with (offline_parts / "distribution.json").open("rb") as source:
                    raw = source.read(1024 * 1024 + 1)
                dist = authenticated_bytes(raw, trust)
            else:
                dist = authenticated_distribution(trust)
            path = install(dist, root, lambda message: messages.put(("status", message)), stop.is_set, offline_parts)
            messages.put(("ready", path))
        except Exception as exc:
            messages.put(("error", "Setup incomplete: " + str(exc)))
    def begin():
        nonlocal worker
        button.configure(state="disabled")
        worker = threading.Thread(target=perform, args=(Path(directory.get()), offline), daemon=False)
        worker.start()
    def choose_offline():
        nonlocal offline
        selected = filedialog.askdirectory(title="Select folder with distribution.json and all archive parts")
        if selected:
            offline = Path(selected)
            label.configure(text="Offline setup selected. The downloaded parts and metadata will be authenticated before installation.")
    tk.Button(ui, text="Use downloaded parts (offline)", command=choose_offline).pack(anchor="w", padx=24, pady=8)
    def launch():
        subprocess.Popen([str(installed / "Aster.exe")], cwd=installed, creationflags=subprocess.CREATE_NO_WINDOW)
        ui.destroy()
    button = tk.Button(ui, text="Install Aster", command=begin)
    button.pack(anchor="e", padx=24, pady=16)
    for child in ui.winfo_children():
        if isinstance(child, tk.Button):
            child.configure(bg="#192530", fg="#e8edf2", activebackground="#16332d", activeforeground="#e8edf2", relief="flat", padx=14, pady=8, font=("Segoe UI", 11))
        elif isinstance(child, tk.Entry):
            child.configure(bg="#192530", fg="#e8edf2", insertbackground="#7de0cb", relief="flat", font=("Segoe UI", 11))
    def update():
        nonlocal installed
        while not messages.empty():
            kind, message = messages.get()
            if kind == "ready":
                installed = message
                label.configure(text="Installation verified. Aster is ready to launch.\nMedical education and research; clinical validation has not been completed.")
                button.configure(text="Launch Aster", command=launch, state="normal")
            else:
                label.configure(text=str(message))
                if kind == "error":
                    button.configure(state="normal")
        ui.after(100, update)
    def close():
        stop.set()
        if worker and worker.is_alive():
            label.configure(text="Pausing setup. Verified downloads will be retained for your next attempt.")
            ui.after(200, close)
        else:
            ui.destroy()
    ui.protocol("WM_DELETE_WINDOW", close)
    update()
    ui.mainloop()


if __name__ == "__main__":
    main()
