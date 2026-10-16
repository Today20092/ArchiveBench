"""Project-aware archive selection; execution stays in the shared job engine."""

import argparse
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .archive import cleanup
from .core import save
from .jobs import run_job
from .presets import resolve_settings
from .selection import selection_defaults, selected_job, project_defaults as project_defaults


def window(sources: Path | list[Path], library: Path, cleanup_mode: bool = False):
    inputs = [sources] if isinstance(sources, Path) else sources
    if cleanup_mode and (len(inputs) != 1 or not inputs[0].is_dir()):
        raise ValueError("Cleanup requires exactly one archive or project folder")
    root, output, files = selection_defaults(inputs)
    form = tk.Tk()
    form.title(
        "ArchiveBench — review archive job"
        if not cleanup_mode
        else "ArchiveBench — separate cleanup"
    )
    form.geometry("1100x720")
    form.minsize(900, 600)
    ttk.Label(
        form,
        text="Select clips and explicit policies. Originals stay intact. Presets are measured starting points, not visual approval.",
    ).pack(anchor="w", padx=12, pady=10)
    tree = ttk.Treeview(
        form, columns=("selected", "file", "size"), show="headings", selectmode="extended"
    )
    for col, title, width in [
        ("selected", "Selected", 70),
        ("file", "Source file", 760),
        ("size", "MiB", 90),
    ]:
        tree.heading(col, text=title)
        tree.column(col, width=width)
    tree.pack(fill="both", expand=True, padx=12)
    choices: dict[str, str] = {}
    if cleanup_mode:
        from .acceptance import inspect_acceptance

        if (root / ".archive-reencoder.json").exists():
            form.destroy()
            raise ValueError("Legacy Proxy Watcher job: use its retained legacy cleanup runner")
        root = root if (root / "archive-manifest.json").exists() else output
        state = inspect_acceptance(root)
        for i, row in enumerate(state["eligible"]):
            key = str(i)
            choices[key] = row["source"]
            tree.insert("", "end", iid=key, values=("No", row["source"], "verified"))
        ttk.Label(
            form,
            text=f"{len(choices)} eligible originals. Visual AND editor acceptance must already be recorded. Nothing is selected by default.",
        ).pack(padx=12, pady=8)
    else:
        for i, (path, checked) in enumerate(files):
            key = str(i)
            choices[key] = path.relative_to(root).as_posix()
            tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    "Yes" if checked else "No",
                    choices[key],
                    round(path.stat().st_size / 1024**2, 1),
                ),
            )

    def toggle(event=None):
        for key in tree.selection():
            tree.set(key, "selected", "No" if tree.set(key, "selected") == "Yes" else "Yes")

    tree.bind("<Double-1>", toggle)
    tree.bind("<space>", toggle)
    row = ttk.Frame(form)
    row.pack(fill="x", padx=12, pady=6)

    def mark(value):
        for key in choices:
            tree.set(key, "selected", value)

    ttk.Button(row, text="Toggle selected rows", command=toggle).pack(side="left")
    ttk.Button(row, text="Select all", command=lambda: mark("Yes")).pack(side="left")
    ttk.Button(row, text="Select none", command=lambda: mark("No")).pack(side="left")
    result = {}
    if not cleanup_mode:
        presets = sorted(library.glob("*.json"))
        if not presets:
            form.destroy()
            raise ValueError(f"No saved presets in {library}")
        preferences = (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
            / "ArchiveBench"
            / "desktop-preferences.json"
        )
        prior = {}
        if preferences.exists():
            try:
                prior = json.loads(preferences.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        destination = tk.StringVar(value=str(output))

        def add_paths(paths):
            nonlocal root, output, files, inputs
            if not paths:
                return
            try:
                previous = {root / choices[k]: tree.set(k, "selected") == "Yes" for k in choices}
                new_inputs = inputs + [Path(p) for p in paths]
                new_root, new_output, new_files = selection_defaults(new_inputs)
                rows = [(p, previous.get(p, checked)) for p, checked in new_files]
                if destination.get() == str(output):
                    destination.set(str(new_output))
                inputs, root, output, files = new_inputs, new_root, new_output, rows
                tree.delete(*tree.get_children())
                choices.clear()
                for i, (p, checked) in enumerate(rows):
                    key = str(i)
                    choices[key] = p.relative_to(root).as_posix()
                    tree.insert(
                        "",
                        "end",
                        iid=key,
                        values=(
                            "Yes" if checked else "No",
                            choices[key],
                            round(p.stat().st_size / 1024**2, 1),
                        ),
                    )
            except (ValueError, OSError) as error:
                messagebox.showerror("Cannot add sources", str(error))

        def add_folder():
            path = filedialog.askdirectory()
            if path:
                add_paths([path])

        ttk.Button(row, text="Add folder", command=add_folder).pack(side="left")
        ttk.Button(
            row, text="Add files", command=lambda: add_paths(filedialog.askopenfilenames())
        ).pack(side="left")
        chosen = tk.StringVar(value=presets[0].name)
        if prior.get("preset") in [p.name for p in presets]:
            chosen.set(prior["preset"])
        if prior.get("source") == str(root):
            destination.set(prior.get("output", str(output)))
        fields = ttk.Frame(form)
        fields.pack(fill="x", padx=12, pady=4)
        ttk.Label(fields, text="Destination").grid(row=0, column=0, sticky="w")
        ttk.Entry(fields, textvariable=destination, width=80).grid(
            row=0, column=1, columnspan=3, sticky="we"
        )

        def browse():
            selected = filedialog.askdirectory()
            if selected:
                destination.set(selected)

        ttk.Button(fields, text="Browse", command=browse).grid(row=0, column=4)
        ttk.Label(fields, text="Measured preset").grid(row=1, column=0, sticky="w")
        ttk.Combobox(
            fields,
            textvariable=chosen,
            values=[p.name for p in presets],
            state="readonly",
            width=55,
        ).grid(row=1, column=1, columnspan=3, sticky="w")
        container, audio, data, tc, drops = (
            tk.StringVar(value=v) for v in ("mov", "copy", "reject", "preserve", "")
        )
        for i, (label, variable, values) in enumerate(
            [
                ("Container", container, ["mov", "mp4", "mkv"]),
                ("Audio", audio, ["copy", "aac", "none"]),
                ("Other data / cover art", data, ["reject", "drop"]),
                ("Timecode", tc, ["preserve", "reject", "drop"]),
            ],
            2,
        ):
            ttk.Label(fields, text=label).grid(row=i, column=0, sticky="w")
            ttk.Combobox(fields, textvariable=variable, values=values, state="readonly").grid(
                row=i, column=1, sticky="w"
            )
        ttk.Label(fields, text="Drop audio tracks (1-based; blank keeps all)").grid(
            row=6, column=0, sticky="w"
        )
        ttk.Entry(fields, textvariable=drops).grid(row=6, column=1, sticky="w")
        detail = tk.StringVar()
        ttk.Label(form, textvariable=detail, wraplength=1050).pack(fill="x", padx=12, pady=6)

        def describe(*args):
            document = json.loads((library / chosen.get()).read_text(encoding="utf-8"))
            settings = resolve_settings(document)
            chroma = (
                "source chroma PRESERVED"
                if settings["pixel_format"] == "source"
                else settings["pixel_format"]
                + " — REDUCED chroma for 4:2:2 sources if output is 4:2:0"
            )
            detail.set(
                f"{document.get('name', chosen.get())}: {settings['encoder']} quality {settings['quality']}; {chroma}. Resolution: {settings.get('resolution', 'original')}. AAC uses 192 kbps/channel. Explicit drop choices omit those streams. Failed clips keep originals; eligible later clips continue."
            )

        chosen.trace_add("write", describe)
        describe()

        def start():
            try:
                selected = [choices[k] for k in choices if tree.set(k, "selected") == "Yes"]
                policies = {
                    "container": container.get(),
                    "audio_mode": audio.get(),
                    "data_mode": data.get(),
                    "timecode_mode": tc.get(),
                    "drop_audio_tracks": [
                        int(x.strip()) for x in drops.get().split(",") if x.strip()
                    ],
                }
                job = selected_job(
                    root, Path(destination.get()), library / chosen.get(), selected, policies
                )
                path = Path(str(job["output_root"]) + ".job.json")
                if path.exists():
                    if json.loads(path.read_text(encoding="utf-8")) != job:
                        raise ValueError(
                            "Existing job differs. Choose another destination; saved jobs stay unchanged."
                        )
                else:
                    save(path, job)
                save(
                    preferences,
                    {"source": str(root), "output": destination.get(), "preset": chosen.get()},
                )
                result["job"] = path
                form.destroy()
            except (ValueError, OSError) as error:
                messagebox.showerror("Cannot start", str(error))

        ttk.Button(form, text="Review preflight for selected clips", command=start).pack(pady=10)
    else:

        def remove():
            selected = [choices[k] for k in choices if tree.set(k, "selected") == "Yes"]
            if selected and messagebox.askyesno(
                "Permanent deletion",
                f"Delete {len(selected)} accepted, verified originals? All checks will run again.",
            ):
                result.update(output=root, selected=selected)
                form.destroy()

        ttk.Button(form, text="Delete selected accepted originals", command=remove).pack(pady=10)
    return form, result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--preset-directory", type=Path, default=Path.home() / "Documents" / "ArchiveBench Presets"
    )
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    form, selection = window(args.root, args.preset_directory, args.cleanup)
    form.mainloop()
    if "job" in selection:
        run_job(selection["job"])
        if (
            input("Type ARCHIVE to execute/resume this reviewed job (anything else cancels): ")
            == "ARCHIVE"
        ):
            run_job(selection["job"], True)
    elif "selected" in selection:
        cleanup(selection["output"], True, True, selected_sources=selection["selected"])


if __name__ == "__main__":
    main()
