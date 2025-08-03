# wipe_loinc.py
from models import Loinc
from database import SyncSession

with SyncSession() as db:
    db.query(Loinc).delete()
    db.commit()
    print("LOINC table cleared.")
