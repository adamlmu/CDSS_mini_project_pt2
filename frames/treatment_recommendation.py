# frames/treatment_recommendation.py
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

    tk.Label(frame, text="Treatment Recommendation", font=("Helvetica", 16)).pack(pady=(0, 10))

    form = tk.Frame(frame, bg="white")
    form.pack()

    pid_entry = tk.Entry(form, width=40)
    time_entry = tk.Entry(form, width=40)

    tk.Label(form, text="Patient ID", bg="white").grid(row=0, column=0, sticky="w", pady=5)
    pid_entry.grid(row=0, column=1, pady=5)

    tk.Label(form, text="Time (dd/mm/YYYY HH:MM or now)", bg="white").grid(row=1, column=0, sticky="w", pady=5)
    time_entry.grid(row=1, column=1, pady=5)

    output = scrolledtext.ScrolledText(frame, width=80, height=18)
    output.pack(pady=(10, 0))

    def submit():
        try:
            pid = int(pid_entry.get().strip())
            time = datetime.utcnow() if time_entry.get().strip().lower() == "now" else datetime.strptime(time_entry.get(), "%d/%m/%Y %H:%M")
        except Exception as e:
            messagebox.showerror("Error", f"Input error: {e}")
            return

        threading.Thread(target=lambda: asyncio.run(fetch_recommendation(pid, time))).start()

    async def fetch_recommendation(pid, time_point):
        async with SessionLocal() as db:
            result = await crud.get_current_treatment_at_time(db, pid, time_point)
            print(result)
            if isinstance(result, str):
                output_text = f"⚠️ {result}"
            else:
                chills_map = {0: "None", 1: "Shaking", 2: "Rigor"}
                skin_map = {0: "Erythema", 1: "Vesiculation", 2: "Desquamation", 3: "Exfoliation"}
                allergy_map = {0: "Edema", 1: "Bronchospasm", 2: "Severe-Bronchospasm", 3: "Anaphylactic-Shock"}
                output_text = (
                    f"Gender: {result['gender']}\n"
                    f"Hemoglobin: {result['hemoglobin_value']} → {result['hemoglobin_state']}\n"
                    f"WBC: {result['wbc_value']} → {result['hematological_state']}\n"
                    f"Toxicity Grade: {result['toxicity_grade']}\n\n"
                    f"Recommended Treatment:\n"
                )
                for line in result['treatment']:
                    output_text += f"  • {line}\n"

            output.delete("1.0", tk.END)
            output.insert(tk.END, output_text)

    tk.Button(frame, text="Get Recommendation", command=submit).pack(pady=10)
