# frames/add_patient.py
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import asyncio
import threading

from app.schemas import PatientCreate
from app.database import SessionLocal
from app import crud

def render(parent):
    frame = tk.Frame(parent, bg="white")
    frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    tk.Label(frame, text="Add Patient", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=(0, 10))

    labels = ["First Name", "Last Name", "Gender (M/F)", "Birth Date (dd/mm/YYYY)"]
    entries = {}

    for i, label in enumerate(labels, 1):
        tk.Label(frame, text=label, bg="white").grid(row=i, column=0, sticky=tk.W, pady=5)
        entry = tk.Entry(frame, width=30)
        entry.grid(row=i, column=1, pady=5)
        entries[label] = entry

    def on_submit():
        first = entries["First Name"].get().strip()
        last = entries["Last Name"].get().strip()
        gender = entries["Gender (M/F)"].get().strip().upper()
        birth_date_raw = entries["Birth Date (dd/mm/YYYY)"].get().strip()

        if not first or not last or gender not in ("M", "F"):
            messagebox.showerror("Input Error", "Please fill in all fields correctly.")
            return

        try:
            birth_date = datetime.strptime(birth_date_raw, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Input Error", "Date must be in format dd/mm/YYYY.")
            return

        data = PatientCreate(first_name=first, last_name=last, gender=gender, birth_date=birth_date)
        threading.Thread(target=create_patient_threadsafe, args=(data,)).start()

    def create_patient_threadsafe(data):
        asyncio.run(run_create_patient(data))

    async def run_create_patient(data):
        async with SessionLocal() as db:
            try:
                patient = await crud.create_patient(db, data)
                messagebox.showinfo("Success", f"Created patient ID: {patient.patient_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create patient:\n{e}")

    submit_btn = tk.Button(frame, text="Submit", command=on_submit)
    submit_btn.grid(row=len(labels) + 1, column=0, columnspan=2, pady=20)
