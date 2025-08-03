# frames/show_history.py
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime
import asyncio
import threading

from app.database import SessionLocal
from app import crud

def render(parent):
    frame = tk.Frame(parent, bg="white")
    frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    tk.Label(frame, text="Show Observation History", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=(0, 10))

    labels = [
        "Patient ID",
        "LOINC Code",
        "Since (dd/mm/YYYY HH:MM or now)",
        "Until (dd/mm/YYYY HH:MM or now)"
    ]
    entries = {}

    for i, label in enumerate(labels, 1):
        tk.Label(frame, text=label, bg="white").grid(row=i, column=0, sticky=tk.W, pady=5)
        entry = tk.Entry(frame, width=40)
        entry.grid(row=i, column=1, pady=5)
        entries[label] = entry

    output = scrolledtext.ScrolledText(frame, width=70, height=15)
    output.grid(row=len(labels)+1, column=0, columnspan=2, pady=(10, 0))

    def on_submit():
        try:
            pid = int(entries["Patient ID"].get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Patient ID must be numeric.")
            return

        loinc = entries["LOINC Code"].get().strip()
        since_raw = entries["Since (dd/mm/YYYY HH:MM or now)"].get().strip().lower()
        until_raw = entries["Until (dd/mm/YYYY HH:MM or now)"].get().strip().lower()

        try:
            since = datetime.utcnow() if since_raw == "now" else datetime.strptime(since_raw, "%d/%m/%Y %H:%M")
            until = datetime.utcnow() if until_raw == "now" else datetime.strptime(until_raw, "%d/%m/%Y %H:%M")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid date format.")
            return

        threading.Thread(target=fetch_history_threadsafe, args=(pid, loinc, since, until)).start()

    def fetch_history_threadsafe(pid, loinc, since, until):
        asyncio.run(run_fetch_history(pid, loinc, since, until))

    async def run_fetch_history(pid, loinc, since, until):
        async with SessionLocal() as db:
            hist = await crud.observations_history(db, pid, loinc, since, until)
            name = await crud.get_loinc_name(db, loinc) or "(no name)"
            output_text = f"LOINC: {loinc} – {name}\n\n"

            if not hist:
                output_text += "No results found."
            else:
                for o in hist:
                    output_text += (
                        f"ID={o.obs_id} Value={o.value_num} "
                        f"Valid=({o.valid_start}, {o.valid_end}) "
                        f"Txn=({o.txn_start}, {o.txn_end})\n"
                    )
            output.delete("1.0", tk.END)
            output.insert(tk.END, output_text)

    submit_btn = tk.Button(frame, text="Fetch", command=on_submit)
    submit_btn.grid(row=len(labels)+2, column=0, columnspan=2, pady=10)
