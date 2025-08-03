# frames/add_observation.py
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import asyncio
import threading

from app.schemas import ObservationCreate
from app.database import SessionLocal
from app import crud

# Categorical LOINC value descriptions
LOINC_MAPPINGS = {
    "75326-8": "Chills: 0=None, 1=Shaking, 2=Rigor",
    "39106-0": "Skin Look: 0=Erythema, 1=Vesiculation, 2=Desquamation, 3=Exfoliation",
    "69730-0": "Allergic State: 0=Edema, 1=Bronchospasm, 2=Severe-Bronchospasm, 3=Anaphylactic-Shock"
}

def render(parent):
    frame = tk.Frame(parent, bg="white")
    frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    tk.Label(frame, text="Add Observation", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=(0, 10))

    labels = [
        "Patient ID",
        "LOINC Code",
        "Value",
        "Start Time (dd/mm/YYYY HH:MM or now)",
        "End Time (optional: dd/mm/YYYY HH:MM or now)"
    ]

    entries = {}

    # Patient ID
    tk.Label(frame, text=labels[0], bg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
    pid_entry = tk.Entry(frame, width=35)
    pid_entry.grid(row=1, column=1, pady=5)
    entries[labels[0]] = pid_entry

    # LOINC Code with dynamic hint
    tk.Label(frame, text=labels[1], bg="white").grid(row=2, column=0, sticky=tk.W, pady=5)
    loinc_var = tk.StringVar()
    loinc_entry = tk.Entry(frame, width=35, textvariable=loinc_var)
    loinc_entry.grid(row=2, column=1, pady=5)
    entries[labels[1]] = loinc_entry

    loinc_hint = tk.Label(frame, text="", bg="white", fg="blue", wraplength=400, justify="left")
    loinc_hint.grid(row=2, column=2, padx=10, sticky="w")

    def update_hint(*_):
        code = loinc_var.get().strip()
        loinc_hint.config(text=LOINC_MAPPINGS.get(code, ""))

    loinc_var.trace_add("write", update_hint)

    # Value
    tk.Label(frame, text=labels[2], bg="white").grid(row=3, column=0, sticky=tk.W, pady=5)
    val_entry = tk.Entry(frame, width=35)
    val_entry.grid(row=3, column=1, pady=5)
    entries[labels[2]] = val_entry

    # Start time
    tk.Label(frame, text=labels[3], bg="white").grid(row=4, column=0, sticky=tk.W, pady=5)
    start_entry = tk.Entry(frame, width=35)
    start_entry.grid(row=4, column=1, pady=5)
    entries[labels[3]] = start_entry

    # End time
    tk.Label(frame, text=labels[4], bg="white").grid(row=5, column=0, sticky=tk.W, pady=5)
    end_entry = tk.Entry(frame, width=35)
    end_entry.grid(row=5, column=1, pady=5)
    entries[labels[4]] = end_entry

    def on_submit():
        try:
            patient_id = int(pid_entry.get().strip())
            loinc = loinc_entry.get().strip()
            value = float(val_entry.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Patient ID and Value must be numeric.")
            return

        start_str = start_entry.get().strip().lower()
        end_str = end_entry.get().strip().lower()

        try:
            start = datetime.utcnow() if start_str == "now" else datetime.strptime(start_str, "%d/%m/%Y %H:%M")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid start time format.")
            return

        if end_str == "":
            end = None
        else:
            try:
                end = datetime.utcnow() if end_str == "now" else datetime.strptime(end_str, "%d/%m/%Y %H:%M")
            except ValueError:
                messagebox.showerror("Input Error", "Invalid end time format.")
                return

        data = ObservationCreate(
            patient_id=patient_id,
            loinc_num=loinc,
            value_num=value,
            start=start,
            end=end
        )

        threading.Thread(target=create_observation_threadsafe, args=(data,)).start()

    def create_observation_threadsafe(data):
        asyncio.run(run_create_observation(data))

    async def run_create_observation(data):
        async with SessionLocal() as db:
            try:
                obs = await crud.create_observation(db, data)
                messagebox.showinfo("Success", f"Created observation ID: {obs.obs_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create observation:\n{e}")

    submit_btn = tk.Button(frame, text="Submit", command=on_submit)
    submit_btn.grid(row=6, column=0, columnspan=2, pady=20)
