#!/usr/bin/env python

import os
import asyncio
import random
import pandas as pd
from faker import Faker
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.knowledge_base import hemoglobin_state, hematological_state, treatment_rules
from app.crud import get_hemoglobin_state, get_hematological_state, get_treatment
from app import models
from app.config import DATABASE_URL
from app.database import Base, SessionLocal
from app.models import Loinc
from app import crud, schemas
from app.crud import (
    get_hemoglobin_state,
    get_hematological_state,
    get_treatment,
    get_hemoglobin_state_with_timing,
    infer_state_intervals,
    filter_intervals_by_state,
    observations_history  # ✅ ADD THIS LINE
)


# ── 1) Sync schema & engine ──────────────────────────────────────────────────
sync_url    = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
sync_engine = create_engine(sync_url, future=True)
SyncSession = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=sync_engine)

# ── 2) Seed LOINC locally from CSV ─────────────────────────────────────────────
def seed_loinc_from_csv():
    try:
        df = pd.read_csv(
            "L_TableCore.csv",
            usecols=["LOINC_NUM","LONG_COMMON_NAME"],
            dtype=str
        ).dropna(subset=["LOINC_NUM","LONG_COMMON_NAME"])
    except Exception as e:
        print(f"Skipping LOINC seed ({e})", flush=True)
        return

    with SyncSession() as db:
        count = db.query(Loinc).count()
        if count >= 104673:
            print(f"LOINC already seeded ({count} rows), skipping.", flush=True)
            return

    print(f"Seeding {len(df)} LOINC entries from CSV...", flush=True)
    with SyncSession() as db:
        for _, r in df.iterrows():
            db.merge(Loinc(
                loinc_num   = r["LOINC_NUM"],
                common_name = r["LONG_COMMON_NAME"]
            ))
        db.commit()
    print("Local LOINC seeded.\n", flush=True)

seed_loinc_from_csv()

# ── 3) Date helper functions ──────────────────────────────────────────────────
DATE_IN  = "%d/%m/%Y %H:%M"
DATE_BD  = "%d/%m/%Y"
DATE_OUT = "%d/%m/%Y %H:%M"

def safe_int(prompt: str) -> int:
    while True:
        s = input(prompt)
        try:
            return int(s)
        except ValueError:
            print("Incorrect input – please enter a whole number.", flush=True)

def safe_float(prompt: str) -> float:
    while True:
        s = input(prompt)
        try:
            return float(s)
        except ValueError:
            print("Incorrect input – please enter a numeric value.", flush=True)

def safe_date(prompt: str) -> datetime.date:
    while True:
        s = input(prompt)
        try:
            return datetime.strptime(s, DATE_BD).date()
        except ValueError:
            print("Incorrect input – use format dd/mm/YYYY.", flush=True)

def safe_datetime(prompt: str, allow_now: bool=False) -> datetime:
    while True:
        s = input(prompt)
        if allow_now and s.strip().lower() == "now":
            return datetime.utcnow()
        try:
            return datetime.strptime(s, DATE_IN)
        except ValueError:
            print("Incorrect input – use format dd/mm/YYYY HH:MM or 'now'.", flush=True)

def fmt(dt: datetime) -> str:
    return dt.strftime(DATE_OUT) if dt else "None"

fake = Faker()
PROJECT_DB_PATH = "project_db.xlsx"

# ── 4) CLI interface ─────────────────────────────────────────────────────────
def print_menu():
    print("\nCDSS Terminal Interface", flush=True)
    print("1. Add Patient", flush=True)
    print("2. Add Observation", flush=True)
    print("3. Show Observation History", flush=True)
    print("4. Retroactive Update Observation", flush=True)
    print("5. Delete Latest Observation", flush=True)
    print("6. Create 10 NEW Fake Patients + Seed Observations from Excel", flush=True)
    print("7. Reasoning Demo",flush=True)
    print("8. Show Hemoglobin State Intervals", flush=True)
    print("9. Show Specific Hemoglobin State Intervals", flush=True)
    print("10. Show Treatment Recommendation at Specific Time", flush=True)
    print("11. Exit", flush=True)



async def add_patient():
    print("\n== Add Patient ==", flush=True)
    first  = input("First name: ").strip()
    last   = input("Last name : ").strip()
    gender = input("Gender (M/F): ").strip().upper()
    bd     = safe_date("Birth date (dd/mm/YYYY): ")
    data   = schemas.PatientCreate(first_name=first, last_name=last, gender=gender, birth_date=bd)
    async with SessionLocal() as db:
        p = await crud.create_patient(db, data)
    print(f"Created patient ID={p.patient_id}", flush=True)

async def add_observation():
    print("\n== Add Observation ==", flush=True)
    pid        = safe_int("Patient ID: ")
    loinc      = input("LOINC Code: ").strip()
    if loinc == "75326-8":  # Chills
        print("Chills options: 0=None, 1=Shaking, 2=Rigor")
    elif loinc == "39106-0":  # Skin-look
        print("Skin look options: 0=Erythema, 1=Vesiculation, 2=Desquamation, 3=Exfoliation")
    elif loinc == "69730-0":  # Allergic-state
        print("Allergic state options: 0=Edema, 1=Bronchospasm, 2=Severe-Bronchospasm, 3=Anaphylactic-Shock")
    val        = safe_float("Value: ")
    start      = safe_datetime("Start (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    end_input  = input("End (dd/mm/YYYY HH:MM or now, empty skip): ").strip()
    if end_input.lower() == "now":
        end = datetime.utcnow()
    elif not end_input:
        end = None
    else:
        end = safe_datetime("End (dd/mm/YYYY HH:MM): ")
    data = schemas.ObservationCreate(
        patient_id=pid, loinc_num=loinc,
        value_num=val, start=start, end=end
    )
    async with SessionLocal() as db:
        o = await crud.create_observation(db, data)
    print(f"Created observation ID={o.obs_id}", flush=True)

async def show_history():
    print("\n== Observation History ==", flush=True)
    pid   = safe_int("Patient ID: ")
    loinc = input("LOINC Code: ").strip()
    since = safe_datetime("Since (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    until = safe_datetime("Until (dd/mm/YYYY HH:MM or now): ", allow_now=True)

    # Define mappings for categorical LOINC values
    loinc_value_mappings = {
        "75326-8": {0: "None", 1: "Shaking", 2: "Rigor"},  # Chills
        "39106-0": {0: "Erythema", 1: "Vesiculation", 2: "Desquamation", 3: "Exfoliation"},  # Skin-look
        "69730-0": {0: "Edema", 1: "Bronchospasm", 2: "Severe-Bronchospasm", 3: "Anaphylactic-Shock"}  # Allergic-state
    }

    async with SessionLocal() as db:
        name = await crud.get_loinc_name(db, loinc) or "(no name)"
        hist = await crud.observations_history(db, pid, loinc, since, until)

    if not hist:
        print("No results.", flush=True)
        return

    print(f"\nLOINC: {loinc} – {name}", flush=True)
    for o in hist:
        display_value = o.value_num
        if loinc in loinc_value_mappings:
            display_value = loinc_value_mappings[loinc].get(int(o.value_num), f"Unknown({o.value_num})")

        print(
            f"ID={o.obs_id} value={display_value} "
            f"valid=({fmt(o.valid_start)},{fmt(o.valid_end)}) "
            f"txn=({fmt(o.txn_start)},{fmt(o.txn_end)})",
            flush=True
        )

async def retro_update():
    print("\n== Retroactive Update ==", flush=True)
    name = input("Patient full name (First Last): ").strip()
    test_input = input("Test name or LOINC Code: ").strip()

    async with SessionLocal() as db:
        # Determine whether it's a code or a name
        loinc = test_input if "-" in test_input else await crud.get_loinc_code_by_name(db, test_input)
        if not loinc:
            print("Test not found by name or code.", flush=True)
            return

        common_name = await crud.get_loinc_name(db, loinc) or "(no name)"
        print(f"Resolved test: {loinc} – {common_name}", flush=True)

        # Show value options if needed
        if loinc == "75326-8":
            print("Chills options: 0=None, 1=Shaking, 2=Rigor", flush=True)
        elif loinc == "39106-0":
            print("Skin look options: 0=Erythema, 1=Vesiculation, 2=Desquamation, 3=Exfoliation", flush=True)
        elif loinc == "69730-0":
            print("Allergic state options: 0=Edema, 1=Bronchospasm, 2=Severe-Bronchospasm, 3=Anaphylactic-Shock", flush=True)

    measured = safe_datetime("Measured at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    txn_at = safe_datetime("Update at (dd/mm/YYYY HH:MM or now): ", allow_now=True)

    if loinc in ("75326-8", "39106-0", "69730-0"):
        try:
            new_val = float(input("New value (use number from options): ").strip())
        except ValueError:
            print("Invalid input – must be numeric index from options.", flush=True)
            return
    else:
        new_val = safe_float("New value: ")

    # Execute update
    async with SessionLocal() as db:
        changed = await crud.retroactive_update(
            db, name, loinc_code=loinc,
            measured_at=measured, txn_at=txn_at,
            new_value=new_val
        )
        if not changed:
            print("No matching observation.", flush=True)
        else:
            old, new = changed
            print(f"\nLOINC: {loinc} – {common_name}", flush=True)
            print(f"[old] ID={old.obs_id} value={old.value_num} txn_end={fmt(old.txn_end)}", flush=True)
            print(f"[new] ID={new.obs_id} value={new.value_num} txn_start={fmt(new.txn_start)}", flush=True)

    # == Retroactive Delete ==
    print("\n== Retroactive Delete ==", flush=True)
    name = input("Patient full name (First Last): ").strip()
    test_input = input("Test name or LOINC Code: ").strip()

    async with SessionLocal() as db:
        loinc = test_input if "-" in test_input else await crud.get_loinc_code_by_name(db, test_input)
        if not loinc:
            print("Test not found by name or code.", flush=True)
            return
        common_name = await crud.get_loinc_name(db, loinc) or "(no name)"

    delete_at = safe_datetime("Delete at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    meas_i = input("Measured at (optional, dd/mm/YYYY HH:MM or now; empty): ").strip()
    if meas_i.lower() == "now":
        measured = datetime.utcnow()
    elif not meas_i:
        measured = None
    else:
        measured = safe_datetime("Measured at (dd/mm/YYYY HH:MM): ")

    async with SessionLocal() as db:
        deleted = await crud.retroactive_delete(
            db, name, loinc_code=loinc,
            delete_at=delete_at, measured_at=measured
        )
        if not deleted:
            print("No matching observation.", flush=True)
        else:
            o = deleted[0]
            print(f"\nLOINC: {loinc} – {common_name}", flush=True)
            print(f"Deleted ID={o.obs_id} value={o.value_num} txn_end={fmt(o.txn_end)}", flush=True)


# async def retro_update():
#     print("\n== Retroactive Update ==", flush=True)
#     name      = input("Patient full name (First Last): ").strip()
#     loinc     = input("LOINC Code: ").strip()

#     # Show value options for categorical LOINCs
#     if loinc == "75326-8":  # Chills
#         print("Chills options: 0=None, 1=Shaking, 2=Rigor", flush=True)
#     elif loinc == "39106-0":  # Skin-look
#         print("Skin look options: 0=Erythema, 1=Vesiculation, 2=Desquamation, 3=Exfoliation", flush=True)
#     elif loinc == "69730-0":  # Allergic state
#         print("Allergic state options: 0=Edema, 1=Bronchospasm, 2=Severe-Bronchospasm, 3=Anaphylactic-Shock", flush=True)

#     measured = safe_datetime("Measured at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
#     txn_at   = safe_datetime("Update at (dd/mm/YYYY HH:MM or now): ", allow_now=True)

#     # Handle input based on LOINC type
#     if loinc in ("75326-8", "39106-0", "69730-0"):
#         try:
#             new_val = float(input("New value (use number from options): ").strip())
#         except ValueError:
#             print("Invalid input – must be numeric index from options.")
#             return
#     else:
#         new_val = safe_float("New value: ")

#     # Execute DB update
#     async with SessionLocal() as db:
#         changed = await crud.retroactive_update(db, name, loinc, measured, txn_at, new_val)

#     if not changed:
#         print("No matching observation.", flush=True)
#     else:
#         old, new = changed
#         common   = (await crud.get_loinc_name(db, loinc)) or "(no name)"
#         print(f"\nLOINC: {loinc} – {common}", flush=True)
#         print(f"[old] ID={old.obs_id} value={old.value_num} txn_end={fmt(old.txn_end)}", flush=True)
#         print(f"[new] ID={new.obs_id} value={new.value_num} txn_start={fmt(new.txn_start)}", flush=True)

#     print("\n== Retroactive Delete ==", flush=True)
#     name      = input("Patient full name (First Last): ").strip()
#     loinc     = input("LOINC Code: ").strip()
#     delete_at = safe_datetime("Delete at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
#     meas_i    = input("Measured at (optional, dd/mm/YYYY HH:MM or now; empty): ").strip()
#     if meas_i.lower() == "now":
#         measured = datetime.utcnow()
#     elif not meas_i:
#         measured = None
#     else:
#         measured = safe_datetime("Measured at (dd/mm/YYYY HH:MM): ")
#     async with SessionLocal() as db:
#         deleted = await crud.retroactive_delete(db, name, loinc, delete_at, measured)
#     if not deleted:
#         print("No matching observation.", flush=True)
#     else:
#         o      = deleted[0]
#         common = (await crud.get_loinc_name(db, loinc)) or "(no name)"
#         print(f"\nLOINC: {loinc} – {common}", flush=True)
#         print(f"Deleted ID={o.obs_id} value={o.value_num} txn_end={fmt(o.txn_end)}", flush=True)

async def create_fake():
    print("\n== Fake Patients + Seed Observations ==", flush=True)

    if not os.path.exists(PROJECT_DB_PATH):
        print(f"File not found: '{PROJECT_DB_PATH}'", flush=True)
        return

    try:
        df = pd.read_excel(PROJECT_DB_PATH, engine="openpyxl")
    except Exception as e:
        print(f"Could not load '{PROJECT_DB_PATH}': {e}", flush=True)
        return

    tests = df.to_dict("records")

    created_patients = []
    created_observations = []

    async with SessionLocal() as db:
        for gender in ("M", "F"):
            for _ in range(5):
                # 1) Create patient
                pdata = schemas.PatientCreate(
                    first_name = fake.first_name_male() if gender == "M" else fake.first_name_female(),
                    last_name  = fake.last_name(),
                    gender     = gender,
                    birth_date = fake.date_of_birth(minimum_age=20, maximum_age=80)
                )
                patient = await crud.create_patient(db, pdata)
                created_patients.append((patient.patient_id, patient.first_name, patient.last_name, patient.gender))

                # 2) Base timestamp
                start = datetime.utcnow()

                # 3) Hemoglobin
                h_value = round(random.uniform(8.0, 17.0), 2)
                obs = await crud.create_observation(db, schemas.ObservationCreate(
                    patient_id = patient.patient_id,
                    loinc_num  = "718-7",
                    value_num  = h_value,
                    start      = start,
                    end        = start + pd.Timedelta(minutes=1)
                ))
                created_observations.append((obs.obs_id, obs.patient_id, obs.loinc_num, obs.value_num))

                # 4) WBC
                wbc_value = round(random.uniform(3000, 12000), 2)
                obs = await crud.create_observation(db, schemas.ObservationCreate(
                    patient_id = patient.patient_id,
                    loinc_num  = "11218-5",
                    value_num  = wbc_value,
                    start      = start,
                    end        = start + pd.Timedelta(minutes=1)
                ))
                created_observations.append((obs.obs_id, obs.patient_id, obs.loinc_num, obs.value_num))

                # 5) Toxicity symptoms (aligned with grade encoding)
                toxicity_tests = [
                    ("8310-5", round(random.uniform(36.5, 41.0), 1)),       # Fever (°C)
                    ("75326-8", random.choice([0, 1, 2])),                 # Chills: None, Shaking, Rigor
                    ("39106-0", random.choice([0, 1, 2, 3])),              # Skin-look: Erythema → Exfoliation
                    ("69730-0", random.choice([0, 1, 2, 3]))               # Allergic-state: Edema → Anaphylactic shock
                ]
                for code, value in toxicity_tests:
                    obs = await crud.create_observation(db, schemas.ObservationCreate(
                        patient_id = patient.patient_id,
                        loinc_num  = code,
                        value_num  = value,
                        start      = start,
                        end        = start + pd.Timedelta(minutes=1)
                    ))
                    created_observations.append((obs.obs_id, obs.patient_id, obs.loinc_num, obs.value_num))

                # 6) Extra Excel observations
                for t in random.sample(tests, min(2, len(tests))):
                    code = t.get("LOINC-NUM")
                    val  = t.get("Value")
                    dt   = t.get("Valid start time")
                    if pd.isna(code) or pd.isna(val) or pd.isna(dt):
                        continue
                    try:
                        num = float(val)
                    except (ValueError, TypeError):
                        print(f"  Skipping non-numeric value {val!r}", flush=True)
                        continue
                    start = pd.to_datetime(dt)
                    obs = await crud.create_observation(db, schemas.ObservationCreate(
                        patient_id = patient.patient_id,
                        loinc_num  = str(code),
                        value_num  = num,
                        start      = start,
                        end        = start + pd.Timedelta(minutes=1)
                    ))
                    created_observations.append((obs.obs_id, obs.patient_id, obs.loinc_num, obs.value_num))

    # summary
    print("\nPatients created:", flush=True)
    for pid, fn, ln, g in created_patients:
        print(f"  • ID={pid}  Name={fn} {ln}  Gender={g}", flush=True)

    print("\nObservations created:", flush=True)
    for oid, pid, lo, val in created_observations:
        print(f"  • ObsID={oid}  PatientID={pid}  LOINC={lo}  Value={val}", flush=True)

def demo_reasoning():
    gender = "Female"
    hemoglobin = 11.5
    wbc = 4200

    h_state = get_hemoglobin_state(gender, hemoglobin)
    hema_state = get_hematological_state(gender, hemoglobin, wbc)
    treatment = get_treatment(gender, h_state, hema_state)

    print(f"Gender: {gender}")
    print(f"Hemoglobin: {hemoglobin} → {h_state}")
    print(f"WBC: {wbc} → {hema_state}")
    print("Recommended treatment:")
    for line in treatment:
        print(f" - {line}")

# ── Hemoglobin State Interval Viewer ────────────────────────────────────────
async def show_hemoglobin_state_intervals():
    print("\n== Hemoglobin State Intervals ==", flush=True)
    
    # Get patient ID and time window
    pid = safe_int("Patient ID: ")
    since = safe_datetime("Since (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    until = safe_datetime("Until (dd/mm/YYYY HH:MM or now): ", allow_now=True)

    # Query observations
    async with SessionLocal() as db:
        hist = await crud.observations_history(db, pid, "718-7", since, until)  # 718-7 is LOINC for Hemoglobin
        if not hist:
            print("No hemoglobin observations found.", flush=True)
            return

        # Get patient gender to apply correct rules
        patient = await db.get(models.Patient, pid)
        gender = "Male" if patient.gender.upper() == "M" else "Female"

        # Build list of (timestamp, value) tuples
        observations = [(o.valid_start, o.value_num) for o in hist]

        # Use temporal reasoning logic from crud.py
        intervals = crud.infer_state_intervals(observations, gender, crud.get_hemoglobin_state_with_timing)


    # Print results
    print(f"\nInferred Hemoglobin States for Patient {pid} ({gender}):", flush=True)
    for row in intervals:
        print(
            f"{row['obs_time']} → {row['state']} "
            f"[valid {row['start']} to {row['end']}] "
            f"(value={row['value']})",
            flush=True
        )

async def show_specific_hemo_state_ranges():
    print("\n== Specific Hemoglobin State Intervals ==", flush=True)
    pid = safe_int("Patient ID: ")
    target_state = input("State to search for (e.g., Severe Anemia): ").strip()
    since = safe_datetime("Since (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    until = safe_datetime("Until (dd/mm/YYYY HH:MM or now): ", allow_now=True)

    async with SessionLocal() as db:
        hist = await observations_history(db, pid, "718-7", since, until)
        if not hist:
            print("No hemoglobin observations found.", flush=True)
            return

        patient = await db.get(models.Patient, pid)
        gender = "Male" if patient.gender.upper() == "M" else "Female"
        observations = [(o.valid_start, o.value_num) for o in hist]
        intervals = infer_state_intervals(observations, gender, get_hemoglobin_state_with_timing)
        filtered = filter_intervals_by_state(intervals, target_state)

    if not filtered:
        print(f"No intervals found for state '{target_state}'.", flush=True)
        return

    print(f"\nPatient {pid} had '{target_state}' during:", flush=True)
    for row in filtered:
        print(f"  From {row['start']} to {row['end']} (value={row['value']})", flush=True)

async def show_treatment_recommendation():
    print("\n== Treatment Recommendation ==", flush=True)
    pid = safe_int("Patient ID: ")
    time_point = safe_datetime("Time to evaluate (dd/mm/YYYY HH:MM or now): ", allow_now=True)

    async with SessionLocal() as db:
        result = await crud.get_current_treatment_at_time(db, pid, time_point)

        if isinstance(result, str):
            print(f"⚠️ {result}", flush=True)
            return

        # Print basic state info
        print(f"\nGender: {result['gender']}")
        print(f"Hemoglobin: {result['hemoglobin_value']} → {result['hemoglobin_state']}")
        print(f"WBC: {result['wbc_value']} → {result['hematological_state']}")

        # Value label mappings
        chills_map = {0: "None", 1: "Shaking", 2: "Rigor"}
        skin_map = {0: "Erythema", 1: "Vesiculation", 2: "Desquamation", 3: "Exfoliation"}
        allergy_map = {0: "Edema", 1: "Bronchospasm", 2: "Severe-Bronchospasm", 3: "Anaphylactic-Shock"}

        # Fetch toxicity-related values
        async def fetch_val(loinc):
            q = await db.execute(
                select(models.Observation)
                .where(models.Observation.patient_id == pid)
                .where(models.Observation.loinc_num == loinc)
                .where(models.Observation.valid_start <= time_point)
                .where((models.Observation.valid_end == None) | (models.Observation.valid_end >= time_point))
                .order_by(models.Observation.valid_start.desc())
            )
            return q.scalars().first()

        chills_obs = await fetch_val("75326-8")
        skin_obs = await fetch_val("39106-0")
        allergy_obs = await fetch_val("69730-0")

        print("\nToxicity-related Observations:")
        if chills_obs:
            print(f"Chills: {chills_map.get(int(chills_obs.value_num), f'Unknown({chills_obs.value_num})')}")
        else:
            print("Chills: Not available")

        if skin_obs:
            print(f"Skin look: {skin_map.get(int(skin_obs.value_num), f'Unknown({skin_obs.value_num})')}")
        else:
            print("Skin look: Not available")

        if allergy_obs:
            print(f"Allergic state: {allergy_map.get(int(allergy_obs.value_num), f'Unknown({allergy_obs.value_num})')}")
        else:
            print("Allergic state: Not available")

        # Final treatment recommendation
        print("\nRecommended treatment:")
        for line in result["treatment"]:
            print(f" - {line}")





async def main():
    while True:
        print_menu()
        choice = input("Choose: ").strip()
        if   choice == "1": await add_patient()
        elif choice == "2": await add_observation()
        elif choice == "3": await show_history()
        elif choice == "4": await retro_update()
        elif choice == "5": await retro_delete()
        elif choice == "6": await create_fake()
        elif choice == "7": await demo_reasoning()
        elif choice == "8": await show_hemoglobin_state_intervals()
        elif choice == "9": await show_specific_hemo_state_ranges()
        elif choice == "10": await show_treatment_recommendation()
        elif choice == "11": break
        else:
            print("Invalid choice, please try again.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())




