"""AsterSetup-Windows-x64: native per-user installer, repair and uninstall.

The release lock (trust root) is compiled into the executable. Command line:
  --auto            start installing with recommended options (window still shown)
  --quiet           no window (automation); write progress to --status-file
  --repair | --rollback | --uninstall [--remove-data]
  --install-dir DIR --profile NAME --no-nc --no-desktop-icon
  --offline-dir DIR install from a folder holding the release assets (no internet)
  --mirror URL      alternative base URL serving the same pinned files (testing/LAN)
  --no-shortcuts --no-register   (testing only)
"""
import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path


def bundled_lock():
    if getattr(sys, "frozen", False):
        return json.loads((Path(sys._MEIPASS) / "release-lock.json").read_text(encoding="utf-8"))
    return json.loads((Path(__file__).resolve().parents[2] / "release" / "release-lock.json").read_text(encoding="utf-8"))


def parse(argv=None):
    parser = argparse.ArgumentParser(prog="AsterSetup")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--remove-data", action="store_true")
    parser.add_argument("--install-dir")
    parser.add_argument("--writable-dir")
    parser.add_argument("--profile")
    parser.add_argument("--no-nc", action="store_true")
    parser.add_argument("--no-desktop-icon", action="store_true")
    parser.add_argument("--offline-dir")
    parser.add_argument("--mirror")
    parser.add_argument("--no-shortcuts", action="store_true")
    parser.add_argument("--no-register", action="store_true")
    parser.add_argument("--registry-key")
    parser.add_argument("--shortcut-dir", action="append")
    parser.add_argument("--status-file")
    parser.add_argument("--launch", action="store_true", help="start Aster after a quiet install")
    parser.add_argument("--portable", help="self-contained folder (USB/offline copy): no shortcuts, registry or "
                                           "%%LOCALAPPDATA%% data; user data stays in <folder>\\UserData")
    return parser.parse_args(argv)


def make_installer(args, lock, notify, cancelled):
    from aster_release.setup_engine import UNINSTALL_KEY, Installer

    install_dir = args.install_dir
    if not install_dir and (args.repair or args.uninstall or args.rollback) and getattr(sys, "frozen", False):
        candidate = Path(sys.executable).parent
        if (candidate / "current.json").exists():
            install_dir = str(candidate)
    return Installer(lock, install_dir, args.writable_dir, mirror=args.mirror, offline_dir=args.offline_dir, notify=notify,
                     cancelled=cancelled, setup_exe=sys.executable if getattr(sys, "frozen", False) else None,
                     shortcuts=not args.no_shortcuts, register=not args.no_register,
                     desktop_icon=not args.no_desktop_icon, shortcut_dirs=args.shortcut_dir,
                     registry_key=args.registry_key or UNINSTALL_KEY)


def run_quiet(args, lock):
    from aster_release.setup_engine import hardware, recommend_profile

    status = Path(args.status_file) if args.status_file else None
    started = time.monotonic()

    def notify(stage, detail, done=None, total=None):
        line = {"stage": stage, "detail": detail, "done": done, "total": total, "elapsed": round(time.monotonic() - started, 1)}
        if status:
            status.parent.mkdir(parents=True, exist_ok=True)
            status.write_text(json.dumps(line), encoding="utf-8")
        else:
            print(json.dumps(line), flush=True)

    installer = make_installer(args, lock, notify, lambda: False)
    try:
        if args.uninstall:
            result = installer.uninstall(args.remove_data)
        elif args.repair:
            result = installer.repair()
        elif args.rollback:
            result = installer.rollback()
        else:
            profile = args.profile or recommend_profile(hardware(installer.install_root), lock)[0]
            result = installer.run(profile, include_nc=not args.no_nc)
            if args.launch:
                launch(Path(result["version_dir"]))
            result = {k: str(v) for k, v in result.items() if k != "plan"}
        notify("finished", json.dumps(result, default=str)[:2000], 1, 1)
        return 0
    except Exception as exc:  # report a readable error; never a stack trace to the user
        notify("error", str(exc))
        return 1


def launch(version_dir):
    subprocess.Popen([str(version_dir / "Aster.exe")], cwd=str(version_dir), creationflags=0x08000000)


def run_window(args, lock):
    import tkinter as tk
    from tkinter import filedialog, ttk

    from aster_release.setup_engine import (
        default_install_root,
        fmt,
        hardware,
        make_plan,
        recommend_profile,
    )

    ui = tk.Tk()
    ui.title("Aster setup")
    ui.geometry("700x560")
    ui.minsize(620, 520)
    colours = {"bg": "#0d141a", "fg": "#e8edf2", "muted": "#b4c1cc", "accent": "#79d9c6", "panel": "#192530"}
    ui.configure(bg=colours["bg"])
    style = ttk.Style(ui)
    style.theme_use("clam")
    style.configure("Aster.Horizontal.TProgressbar", troughcolor=colours["panel"], background=colours["accent"], thickness=14)
    messages, stop = queue.Queue(), threading.Event()
    state = {"worker": None, "result": None, "plan": None}

    def label(text, size=11, colour="fg", **pack):
        widget = tk.Label(ui, text=text, bg=colours["bg"], fg=colours[colour], font=("Segoe UI", size), justify="left",
                          wraplength=640, anchor="w")
        widget.pack(fill="x", padx=28, **pack)
        return widget

    mode = "Repair" if args.repair else "Uninstall" if args.uninstall else "Rollback" if args.rollback else "Install"
    label("Aster " + ("setup" if mode == "Install" else mode.lower()), 22, "accent", pady=(22, 6))
    intro = label("Aster runs on this computer. First-time setup downloads the AI models, text reader, X-ray checker and "
                  "medical reference library (several GB) and can take from about 15 minutes to over an hour depending on "
                  "your connection. After that, Aster works offline. No account, API key or extra software is needed.",
                  11, "muted")
    if mode != "Install":
        intro.configure(text={"Repair": "Checks every installed file and re-downloads anything missing or damaged.",
                              "Uninstall": "Removes Aster, its shortcuts and its uninstall entry. Choose whether to also remove "
                                           "downloads, logs and saved study notes.",
                              "Rollback": "Switches back to the previously installed Aster version."}[mode])
    hw = hardware(args.install_dir or default_install_root())
    recommended, reasons = recommend_profile(hw, lock)
    profile_var = tk.StringVar(value=args.profile or recommended)
    folder_var = tk.StringVar(value=args.install_dir or str(default_install_root()))
    nc_var = tk.BooleanVar(value=not args.no_nc)
    desktop_var = tk.BooleanVar(value=not args.no_desktop_icon)
    remove_data_var = tk.BooleanVar(value=args.remove_data)
    options = tk.Frame(ui, bg=colours["bg"])
    options.pack(fill="x", padx=28, pady=10)
    summary = tk.Label(ui, text="", bg=colours["bg"], fg=colours["fg"], font=("Segoe UI", 10), justify="left", wraplength=640, anchor="w")

    def refresh_summary(*_):
        if mode != "Install":
            return
        try:
            from aster_release.setup_engine import Installer

            downloads = Installer(lock, folder_var.get(), args.writable_dir).downloads
            plan = make_plan(lock, profile_var.get(), folder_var.get(), downloads, nc_var.get())
            state["plan"] = plan
            free = hardware(folder_var.get()).get("free_disk_gb")
            description = lock["profiles"][profile_var.get()]["description"]
            summary.configure(text=f"Download: {fmt(plan.download_bytes)}" + (f" (+{fmt(plan.cached_bytes)} already downloaded)" if plan.cached_bytes else "")
                              + f" · Installed size: {fmt(plan.unpacked_bytes)} · Free space needed: {fmt(plan.required_free_bytes)}"
                              + (f" · Free now: {free} GB" if free is not None else "") + f"\n{description}")
        except Exception as exc:
            summary.configure(text="Could not prepare the plan: " + str(exc))

    if mode == "Install":
        uses_gpu = any(p.get("requires", {}).get("nvidia_vram_gb") for p in lock["profiles"].values())
        gpu = (", ".join(f"{g['name']} ({g['vram_gb']} GB)" for g in hw["gpus"]) or "no NVIDIA GPU detected") if uses_gpu \
            else "runs on the CPU (no graphics card needed)"
        tk.Label(options, text=f"This PC: {hw.get('cpu') or 'CPU'} · {hw.get('ram_gb')} GB RAM · {gpu}", bg=colours["bg"],
                 fg=colours["muted"], font=("Segoe UI", 10), anchor="w").pack(fill="x")
        row = tk.Frame(options, bg=colours["bg"])
        row.pack(fill="x", pady=6)
        tk.Label(row, text="Performance profile:", bg=colours["bg"], fg=colours["fg"], font=("Segoe UI", 10)).pack(side="left")
        names = [n for n in lock.get("profile_order", lock["profiles"])]
        menu = ttk.Combobox(row, textvariable=profile_var, values=names, state="readonly", width=18)
        menu.pack(side="left", padx=8)
        menu.bind("<<ComboboxSelected>>", refresh_summary)
        tk.Label(row, text=f"(recommended: {recommended})", bg=colours["bg"], fg=colours["muted"], font=("Segoe UI", 10)).pack(side="left")
        folder_row = tk.Frame(options, bg=colours["bg"])
        folder_row.pack(fill="x", pady=4)
        tk.Entry(folder_row, textvariable=folder_var, bg=colours["panel"], fg=colours["fg"], insertbackground=colours["accent"],
                 relief="flat", font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
        tk.Button(folder_row, text="Change folder", command=lambda: (folder_var.set(filedialog.askdirectory() or folder_var.get()),
                                                                   refresh_summary())).pack(side="left", padx=6)
        for var, text in ((nc_var, "Include the noncommercial study library (OpenStax and other CC BY-NC textbooks; free for "
                                   "personal and educational use only)"),
                          (desktop_var, "Create a desktop icon")):
            tk.Checkbutton(options, text=text, variable=var, command=refresh_summary, bg=colours["bg"], fg=colours["fg"],
                           selectcolor=colours["panel"], activebackground=colours["bg"], activeforeground=colours["fg"],
                           font=("Segoe UI", 10), wraplength=620, justify="left", anchor="w").pack(fill="x")
        summary.pack(fill="x", padx=28, pady=4)
        refresh_summary()
    elif mode == "Uninstall":
        tk.Checkbutton(options, text="Also remove downloads, logs and saved study notes", variable=remove_data_var,
                       bg=colours["bg"], fg=colours["fg"], selectcolor=colours["panel"], font=("Segoe UI", 10)).pack(anchor="w")
    stage = label("", 12, pady=(8, 2))
    bar = ttk.Progressbar(ui, style="Aster.Horizontal.TProgressbar", mode="determinate", maximum=1000)
    bar.pack(fill="x", padx=28, pady=6)
    detail = label("", 10, "muted")
    buttons = tk.Frame(ui, bg=colours["bg"])
    buttons.pack(side="bottom", fill="x", padx=28, pady=18)
    primary = tk.Button(buttons, text=mode)
    cancel = tk.Button(buttons, text="Cancel")
    for button in (primary, cancel):
        button.configure(bg=colours["panel"], fg=colours["fg"], activebackground="#16332d", activeforeground=colours["fg"],
                         relief="flat", padx=16, pady=8, font=("Segoe UI", 11))
    primary.pack(side="right")
    cancel.pack(side="right", padx=8)
    speed = {"t": time.monotonic(), "done": 0, "rate": 0.0}

    def notify(stage_name, text, done=None, total=None):
        messages.put((stage_name, text, done, total))

    def work():
        args.install_dir, args.no_nc, args.no_desktop_icon = folder_var.get(), not nc_var.get(), not desktop_var.get()
        installer = make_installer(args, lock, notify, stop.is_set)
        try:
            if mode == "Uninstall":
                result = installer.uninstall(remove_data_var.get())
            elif mode == "Repair":
                result = installer.repair()
            elif mode == "Rollback":
                result = installer.rollback()
            else:
                result = installer.run(profile_var.get(), include_nc=nc_var.get())
            messages.put(("finished", result, None, None))
        except Exception as exc:
            messages.put(("error", str(exc), None, None))

    def begin():
        primary.configure(state="disabled")
        stage.configure(text="Starting…")
        state["worker"] = threading.Thread(target=work, daemon=True)
        state["worker"].start()

    def finish(result):
        state["result"] = result
        bar["value"] = 1000
        if mode == "Install":
            stage.configure(text="Aster is installed and verified.")
            detail.configure(text="Use the Aster icon in the Start menu" + (" or on the desktop" if desktop_var.get() else "") +
                             ". Aster is medical education and information software; it does not diagnose or prescribe.")
            primary.configure(text="Launch Aster", state="normal", command=lambda: (launch(Path(result["version_dir"])), ui.destroy()))
        else:
            stage.configure(text=f"{mode} finished.")
            detail.configure(text=json.dumps(result, default=str)[:300] if mode != "Uninstall" else "Aster was removed.")
            primary.configure(text="Close", state="normal", command=ui.destroy)
        cancel.configure(state="disabled")

    def update():
        while not messages.empty():
            stage_name, text, done, total = messages.get()
            if stage_name == "finished":
                finish(text)
            elif stage_name == "error":
                stage.configure(text="Setup could not finish")
                detail.configure(text=text + "\nFinished downloads are kept; choose Retry to continue.")
                primary.configure(text="Retry", state="normal", command=begin)
            else:
                stage.configure(text={"download": "Downloading", "extract": "Installing", "verify": "Verifying",
                                      "library": "Installing the medical library", "plan": "Preparing", "repair": "Repairing",
                                      "done": "Finishing"}.get(stage_name, stage_name.title()))
                line = text
                if done is not None and total:
                    bar["value"] = int(1000 * done / total)
                    if stage_name == "download":
                        now = time.monotonic()
                        if now - speed["t"] > 1:
                            speed["rate"] = 0.7 * speed["rate"] + 0.3 * (done - speed["done"]) / (now - speed["t"])
                            speed["t"], speed["done"] = now, done
                        if speed["rate"] > 0:
                            line += f" · {fmt(speed['rate'])}/s · about {int((total - done) / speed['rate'] / 60) + 1} min left"
                detail.configure(text=line)
        ui.after(150, update)

    def close():
        if state["worker"] and state["worker"].is_alive():
            stop.set()
            stage.configure(text="Pausing… finished downloads are kept for next time.")
            ui.after(300, close)
        else:
            ui.destroy()

    primary.configure(command=begin)
    cancel.configure(command=close)
    ui.protocol("WM_DELETE_WINDOW", close)
    update()
    if args.auto:
        ui.after(400, begin)
    ui.mainloop()
    return 0


def main(argv=None):
    args = parse(argv)
    lock = bundled_lock()
    if args.portable:
        portable = Path(args.portable)
        portable.mkdir(parents=True, exist_ok=True)
        (portable / "portable.json").write_text(json.dumps({"portable": True}), encoding="utf-8")
        args.install_dir, args.writable_dir = str(portable), str(portable / "UserData")
        args.no_shortcuts = args.no_register = args.no_desktop_icon = True
    if args.quiet:
        return run_quiet(args, lock)
    return run_window(args, lock)


if __name__ == "__main__":
    sys.exit(main())
