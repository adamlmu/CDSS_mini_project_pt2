import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import asyncio
import threading

from app.database import SessionLocal
from app import crud

def render(parent):
    notebook = tk.Frame(parent)
    notebook.pack(expand=True, fill=tk.BOTH)

    update_frame = tk.LabelFrame(notebook, text="Retroactive Update", padx=10, pady=10)
    delete_frame = tk.LabelFrame(notebook, text="Retroactive Delete", padx=10, pady=10)

    update_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    delete_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    # ─── UPDATE SECTION ──────────────────────────────────────────────────────
    update_entries = {}
    for i, label in enumerate([
        "Patient Name (First Last)",
        "LOINC Code or Test Name",
        "Measured At (dd/mm/YYYY HH:MM or now)",
        "Txn Update Time (dd/mm/YYYY HH:MM or now)",
        "New Value (use index for categorical)"
    ]):
        tk.Label(update_frame, text=label).grid(row=i, column=0, sticky="w")
        entry = tk.Entry(update_frame, width=40)
        entry.grid(row=i, column=1, pady=2)
        update_entries[label] = entry

    def submit_update():
        name = update_entries["Patient Name (First Last)"].get().strip()
        loinc_input = update_entries["LOINC Code or Test Name"].get().strip()
        try:
            measured = parse_datetime(update_entries["Measured At (dd/mm/YYYY HH:MM or now)"].get())
            txn = parse_datetime(update_entries["Txn Update Time (dd/mm/YYYY HH:MM or now)"].get())
            val = float(update_entries["New Value (use index for categorical)"].get().strip())
        except Exception as e:
            messagebox.showerror("Error", f"Input error: {e}")
            return

        threading.Thread(target=lambda: asyncio.run(run_update(name, loinc_input, measured, txn, val))).start()

    async def run_update(name, loinc_or_name, measured, txn, val):
        async with SessionLocal() as db:
            # Try resolving name to LOINC if needed
            loinc = loinc_or_name if "-" in loinc_or_name else await crud.get_loinc_code_by_name(db, loinc_or_name)
            if not loinc:
                messagebox.showerror("Error", f"Test '{loinc_or_name}' not found.")
                return

            result = await crud.retroactive_update(db, name, loinc, measured, txn, val)
            if not result:
                messagebox.showinfo("Result", "No matching observation found.")
            else:
                messagebox.showinfo("Updated", f"Observation updated for LOINC {loinc}.")

    tk.Button(update_frame, text="Submit Update", command=submit_update).grid(row=6, column=0, columnspan=2, pady=10)

    # ─── DELETE SECTION ──────────────────────────────────────────────────────
    delete_entries = {}
    for i, label in enumerate([
        "Patient Name (First Last)",
        "LOINC Code or Test Name",
        "Delete At (dd/mm/YYYY HH:MM or now)",
        "Measured At (optional, leave blank)"
    ]):
        tk.Label(delete_frame, text=label).grid(row=i, column=0, sticky="w")
        entry = tk.Entry(delete_frame, width=40)
        entry.grid(row=i, column=1, pady=2)
        delete_entries[label] = entry

    def submit_delete():
        name = delete_entries["Patient Name (First Last)"].get().strip()
        loinc_input = delete_entries["LOINC Code or Test Name"].get().strip()
        try:
            delete_at = parse_datetime(delete_entries["Delete At (dd/mm/YYYY HH:MM or now)"].get())
            measured_input = delete_entries["Measured At (optional, leave blank)"].get().strip()
            measured = None if not measured_input else parse_datetime(measured_input)
        except Exception as e:
            messagebox.showerror("Error", f"Input error: {e}")
            return

        threading.Thread(target=lambda: asyncio.run(run_delete(name, loinc_input, delete_at, measured))).start()

    async def run_delete(name, loinc_or_name, delete_at, measured):
        async with SessionLocal() as db:
            loinc = loinc_or_name if "-" in loinc_or_name else await crud.get_loinc_code_by_name(db, loinc_or_name)
            if not loinc:
                messagebox.showerror("Error", f"Test '{loinc_or_name}' not found.")
                return

            result = await crud.retroactive_delete(db, name, loinc, delete_at, measured)
            if not result:
                messagebox.showinfo("Result", "No matching observation found.")
            else:
                messagebox.showinfo("Deleted", f"Observation deleted for LOINC {loinc}.")

    tk.Button(delete_frame, text="Submit Delete", command=submit_delete).grid(row=5, column=0, columnspan=2, pady=10)

# ─── Helpers ────────────────────────────────────────────────────────────────
def parse_datetime(text):
    if text.strip().lower() == "now":
        return datetime.utcnow()
    return datetime.strptime(text, "%d/%m/%Y %H:%M")
