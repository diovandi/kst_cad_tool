"""
Shared dialogs and utility functions for KST UI.
"""

import tkinter as tk

def parse_xyz(s):
    """Parse 'x, y, z' or 'x y z' into three floats (as strings); return ['0','0','0'] for empty/invalid."""
    s = (s or "").strip()
    if not s:
        return ["0", "0", "0"]
    parts = [p.strip() for p in s.replace(",", " ").split()[:3]]
    while len(parts) < 3:
        parts.append("0")
    return parts[:3]


def show_location_orientation_dialog(parent, current_location, current_orientation):
    """
    Show a dialog to enter Location (x,y,z) and Orientation (nx,ny,nz).
    Returns (location_str, orientation_str) on OK, or (None, None) on Cancel.
    """
    loc_parts = parse_xyz(current_location)
    orient_parts = parse_xyz(current_orientation)
    result = [None, None]

    # If parent is None, use root window if available, or create one?
    # Usually parent is expected.

    win = tk.Toplevel(parent)
    win.title("Location & Orientation")
    win.transient(parent)
    win.grab_set()
    try:
        default_bg = win.cget("bg")
    except tk.TclError:
        default_bg = "#d9d9d9"
    f = tk.Frame(win, padx=16, pady=16, bg=default_bg)
    f.pack(fill="both", expand=True)
    tk.Label(f, text="Location (x, y, z):", font=("", 10, "bold"), bg=default_bg).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
    loc_entries = []
    for i, (label, val) in enumerate(zip(["x", "y", "z"], loc_parts)):
        tk.Label(f, text=label + ":", bg=default_bg).grid(row=1, column=i, sticky="w", padx=(0, 4))
        e = tk.Entry(f, width=14)
        e.insert(0, val)
        e.grid(row=2, column=i, sticky="ew", padx=(0, 8))
        loc_entries.append(e)
    tk.Label(f, text="Orientation (nx, ny, nz):", font=("", 10, "bold"), bg=default_bg).grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 4))
    orient_entries = []
    for i, (label, val) in enumerate(zip(["nx", "ny", "nz"], orient_parts)):
        tk.Label(f, text=label + ":", bg=default_bg).grid(row=4, column=i, sticky="w", padx=(0, 4))
        e = tk.Entry(f, width=14)
        e.insert(0, val)
        e.grid(row=5, column=i, sticky="ew", padx=(0, 8))
        orient_entries.append(e)
    def on_ok():
        result[0] = ", ".join(e.get().strip() or "0" for e in loc_entries)
        result[1] = ", ".join(e.get().strip() or "0" for e in orient_entries)
        win.destroy()
    def on_cancel():
        win.destroy()
    btn_f = tk.Frame(f, bg=default_bg)
    btn_f.grid(row=6, column=0, columnspan=3, pady=(16, 0))
    tk.Button(btn_f, text="OK", command=on_ok, width=8).pack(side="left", padx=4)
    tk.Button(btn_f, text="Cancel", command=on_cancel, width=8).pack(side="left", padx=4)
    f.columnconfigure(0, weight=1)
    f.columnconfigure(1, weight=1)
    f.columnconfigure(2, weight=1)
    win.geometry("340x240")
    win.resizable(True, False)
    win.update_idletasks()
    win.lift()
    win.focus_force()
    win.wait_window()
    return (result[0], result[1])
