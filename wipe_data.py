# wipe_patients_and_observations.py

from app.models import Patient, Observation
from app.database import SyncSession

with SyncSession() as db:
    print("Wiping all patients and observations...", flush=True)

    # Delete observations first (foreign key constraint)
    deleted_obs = db.query(Observation).delete()
    print(f"Deleted {deleted_obs} observations.", flush=True)

    # Then delete patients
    deleted_patients = db.query(Patient).delete()
    print(f"Deleted {deleted_patients} patients.", flush=True)

    db.commit()
    print("✅ Done.", flush=True)
