# frames/hemo_intervals.py
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime
import asyncio
import threading

from app.database import SessionLocal
from app import crud, models

def render(parent):
    frame = tk.Frame(parent, bg="white")
    frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    tk.Label(frame, text="Hemoglobin State Intervals", font=("Helvetica", 16)).pack(pady=(0, 10))

    form = tk.Frame(frame, bg="white")
    form.pack()

    entries = {}
    for i, label in enumerate([
        "Patient ID",
        "Since (dd/mm/YYYY HH:MM or now)",
        "Until (dd/mm/YYYY HH:MM or now)"
    ]):
        tk.Label(form, text=label, bg="white").grid(row=i, column=0, sticky="w", pady=5)
        e = tk.Entry(form, width=40)
        e.grid(row=i, column=1, pady=5)
        entries[label] = e

    output = scrolledtext.ScrolledText(frame, width=80, height=15)
    output.pack(pady=(10, 0))

    def submit():
        try:
            pid = int(entries["Patient ID"].get().strip())
            since = parse_dt(entries["Since (dd/mm/YYYY HH:MM or now)"].get().strip())
            until = parse_dt(entries["Until (dd/mm/YYYY HH:MM or now)"].get().strip())
        except Exception as e:
            messagebox.showerror("Error", f"Input error: {e}")
            return

        threading.Thread(target=lambda: asyncio.run(fetch_intervals(pid, since, until))).start()

    async def fetch_intervals(pid, since, until):
        async with SessionLocal() as db:
            hist = await crud.observations_history(db, pid, "718-7", since, until)
            if not hist:
                output_text = "No hemoglobin observations found."
            else:
                patient = await db.get(models.Patient, pid)
                gender = "Male" if patient.gender.upper() == "M" else "Female"
                values = [(o.valid_start, o.value_num) for o in hist]
                intervals = crud.infer_state_intervals(values, gender, crud.get_hemoglobin_state_with_timing)

                output_text = f"Patient {pid} ({gender}) Hemoglobin States:\n\n"
                for row in intervals:
                    output_text += (
                        f"{row['obs_time']} → {row['state']} "
                        f"[valid {row['start']} to {row['end']}] "
                        f"(value={row['value']})\n"
                    )

            output.delete("1.0", tk.END)
            output.insert(tk.END, output_text)

    tk.Button(frame, text="View Intervals", command=submit).pack(pady=10)

def parse_dt(text):
    return datetime.utcnow() if text.strip().lower() == "now" else datetime.strptime(text, "%d/%m/%Y %H:%M")
