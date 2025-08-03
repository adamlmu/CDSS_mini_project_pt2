# frames/patient_status.py
import tkinter as tk
from tkinter import ttk
import asyncio
import threading

from app import models
from app.database import SessionLocal
from sqlalchemy import select

# Selected LOINC codes to monitor
LOINC_CODES = {
    "718-7": "Hemoglobin",
    "11218-5": "WBC",
    "8310-5": "Fever",
    "75326-8": "Chills",
    "39106-0": "Skin",
    "69730-0": "Allergy"
}

TOXICITY_MAPS = {
    "75326-8": {0: "None", 1: "Shaking", 2: "Rigor"},
    "39106-0": {0: "Erythema", 1: "Vesiculation", 2: "Desquamation", 3: "Exfoliation"},
    "69730-0": {0: "Edema", 1: "Bronchospasm", 2: "Severe-Bronchospasm", 3: "Anaphylactic-Shock"}
}

def render(parent):
    frame = tk.Frame(parent, bg="white")
    frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    tk.Label(frame, text="Patient Status Overview", font=("Helvetica", 16)).pack()

    table = ttk.Treeview(frame, columns=("Name", *LOINC_CODES.values()), show="headings")
    for col in table["columns"]:
        table.heading(col, text=col)
        table.column(col, anchor="center", width=100)
    table.pack(expand=True, fill=tk.BOTH, pady=10)

    def fetch_and_display():
        threading.Thread(target=lambda: asyncio.run(populate_table(table))).start()

    async def populate_table(tree):
        async with SessionLocal() as db:
            tree.delete(*tree.get_children())
            patients = await db.execute(select(models.Patient))
            for patient in patients.scalars():
                row = [f"{patient.first_name} {patient.last_name}"]
                for code in LOINC_CODES.keys():
                    obs = await db.execute(
                        select(models.Observation)
                        .where(models.Observation.patient_id == patient.patient_id)
                        .where(models.Observation.loinc_num == code)
                        .order_by(models.Observation.valid_start.desc())
                        .limit(1)
                    )
                    latest = obs.scalars().first()
                    if latest:
                        val = latest.value_num
                        if code in TOXICITY_MAPS:
                            val = TOXICITY_MAPS[code].get(int(val), f"Unknown({val})")
                    else:
                        val = "-"
                    row.append(val)
                tree.insert("", tk.END, values=row)

    tk.Button(frame, text="Refresh", command=fetch_and_display).pack(pady=5)
    fetch_and_display()
