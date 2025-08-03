from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
import pandas as pd
from app.knowledge_base import get_hemoglobin_state_with_timing
from app.models import Observation, Patient
from app.knowledge_base import (
    get_hemoglobin_state_with_timing,
    treatment_rules
)
from app.knowledge_base import get_toxicity_grade_from_features, treatment_rules

async def get_loinc_code_by_name(db: AsyncSession, test_name: str) -> Optional[str]:
    row = (await db.scalars(
        select(models.Loinc).where(models.Loinc.common_name.ilike(f"%{test_name}%"))
    )).first()
    return row.loinc_num if row else None

async def create_patient(db: AsyncSession, data: schemas.PatientCreate) -> models.Patient:
    p = models.Patient(**data.dict())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p

async def create_observation(db: AsyncSession, data: schemas.ObservationCreate) -> models.Observation:
    o = models.Observation(
        patient_id  = data.patient_id,
        loinc_num   = data.loinc_num,
        value_num   = data.value_num,
        valid_start = data.start,
        valid_end   = data.end,
        txn_start   = datetime.utcnow(),
        txn_end     = None
    )
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return o

async def observations_history(
    db: AsyncSession,
    patient_id: int,
    loinc: str,
    since: datetime,
    until: datetime
) -> List[models.Observation]:
    stmt = (
        select(models.Observation)
        .where(models.Observation.patient_id == patient_id)
        .where(models.Observation.loinc_num    == loinc)
        .where(models.Observation.txn_end      == None)
        .where(models.Observation.valid_start <= until)
        .where(or_(
            models.Observation.valid_end == None,
            models.Observation.valid_end >= since
        ))
        .order_by(models.Observation.valid_start)
    )
    return (await db.scalars(stmt)).all()

async def update_observation_value(
    db: AsyncSession,
    obs_id: int,
    new_value: float
) -> Optional[models.Observation]:
    old = await db.get(models.Observation, obs_id)
    if not old:
        return None
    old.txn_end = datetime.utcnow()
    await db.commit()

    new = models.Observation(
        patient_id  = old.patient_id,
        loinc_num   = old.loinc_num,
        value_num   = new_value,
        valid_start = old.valid_start,
        valid_end   = old.valid_end,
        txn_start   = datetime.utcnow(),
        txn_end     = None
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new

from datetime import timedelta

async def retroactive_update(
    db: AsyncSession,
    patient_name: str,
    loinc_code: str,
    measured_at: datetime,
    txn_at: datetime,
    new_value: float
) -> List[models.Observation]:
    first, last = patient_name.split(maxsplit=1)

    p = (await db.scalars(
        select(models.Patient)
        .where(and_(
            models.Patient.first_name == first,
            models.Patient.last_name == last
        ))
    )).first()
    if not p:
        return []

    # חיפוש תצפית בטווח זמן של שנייה
    old = (await db.scalars(
        select(models.Observation)
        .where(models.Observation.patient_id == p.patient_id)
        .where(models.Observation.loinc_num == loinc_code)
        .where(models.Observation.valid_start.between(measured_at, measured_at + timedelta(seconds=1)))
        .order_by(desc(models.Observation.txn_start))
        .limit(1)
    )).first()

    if not old:
        return []

    old.txn_end = txn_at
    await db.commit()

    new = models.Observation(
        patient_id  = old.patient_id,
        loinc_num   = old.loinc_num,
        value_num   = new_value,
        valid_start = old.valid_start,
        valid_end   = old.valid_end,
        txn_start   = txn_at,
        txn_end     = None
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return [old, new]


from datetime import timedelta

async def retroactive_delete(
    db: AsyncSession,
    patient_name: str,
    loinc_code: str,
    delete_at: datetime,
    measured_at: Optional[datetime] = None
) -> List[models.Observation]:
    first, last = patient_name.split(maxsplit=1)

    p = (await db.scalars(
        select(models.Patient)
        .where(and_(
            models.Patient.first_name == first,
            models.Patient.last_name == last
        ))
    )).first()
    if not p:
        return []

    base = select(models.Observation).where(
        models.Observation.patient_id == p.patient_id,
        models.Observation.loinc_num == loinc_code,
        models.Observation.txn_end == None
    )

    old = (await db.scalars(base.order_by(desc(models.Observation.valid_start)).limit(1))).first()
    if not old:
        return []

    old.txn_end = delete_at
    await db.commit()
    return [old]


async def get_loinc_name(db: AsyncSession, loinc_code: str) -> Optional[str]:
    lo = (await db.scalars(
            select(models.Loinc).where(models.Loinc.loinc_num==loinc_code)
          )).first()
    return lo.common_name if lo else None


from app.knowledge_base import hemoglobin_state, hematological_state, treatment_rules

def get_hemoglobin_state(gender: str, value: float) -> str:
    for low, high, label, _, _ in hemoglobin_state[gender]:
        if low <= value < high:
            return label
    return "Unknown"

def get_hematological_state(gender: str, h_value: float, wbc_value: float) -> str:
    for h_range, wbc_map in hematological_state[gender].items():
        if h_range[0] <= h_value < h_range[1]:
            for wbc_range, label in wbc_map.items():
                if wbc_range[0] <= wbc_value < wbc_range[1]:
                    return label
    return "Unknown"

def get_treatment(gender: str, hemo_state: str, hema_state: str) -> list:
    return treatment_rules.get(gender, {}).get((hemo_state, hema_state), ["No recommendation found"])

# Define time validity windows
GOOD_BEFORE = pd.Timedelta(days=1)
GOOD_AFTER = pd.Timedelta(days=3)

def infer_state_intervals(observations: list, gender: str, state_func) -> list:
    """
    Given a list of (obs_time, value), return list of interval dicts
    using dynamic good_before and good_after per state.
    """
    intervals = []
    for obs_time, value in observations:
        result = state_func(gender, value)
        interval = {
            "state": result["state"],
            "start": obs_time - result["good_before"],
            "end": obs_time + result["good_after"],
            "value": value,
            "obs_time": obs_time,
        }
        intervals.append(interval)
    return intervals


def filter_intervals_by_state(intervals: list, target_state: str) -> list:
    """
    Filter a list of interval dicts to only include those matching a given state.

    Parameters:
        intervals (list): List of dicts with keys: 'state', 'start', 'end', etc.
        target_state (str): The state name to filter on, e.g., "Moderate Anemia"

    Returns:
        list of matching intervals
    """
    return [interval for interval in intervals if interval["state"] == target_state]


from datetime import timedelta

async def get_current_treatment_at_time(db, patient_id: int, time_point: datetime):
    """
    Returns treatment recommendation for a patient at a given time, based on Hemoglobin state,
    Hematological state, and Systemic Toxicity grade.
    """
    from .models import Observation, Patient
    from .knowledge_base import toxicity_rules, treatment_rules
    from .crud import get_hemoglobin_state, get_hematological_state, get_toxicity_grade

    # 1. Get patient
    patient = await db.get(Patient, patient_id)
    if not patient:
        return "Patient not found"
    gender = "Male" if patient.gender.upper() == "M" else "Female"

    # Helper to retrieve latest numeric observation for a LOINC code
    async def latest_numeric_value(loinc):
        res = await db.execute(
            select(Observation)
            .where(Observation.patient_id == patient_id)
            .where(Observation.loinc_num == loinc)
            .where(Observation.valid_start <= time_point)
            .where((Observation.valid_end == None) | (Observation.valid_end >= time_point))
            .order_by(Observation.valid_start.desc())
        )
        obs = res.scalars().first()
        return obs.value_num if obs else None

    # 2. Get Hemoglobin and WBC
    h_value = await latest_numeric_value("718-7")      # Hemoglobin
    w_value = await latest_numeric_value("11218-5")     # WBC

    # 3. Get Toxicity-related observations
    fever     = await latest_numeric_value("8310-5")    # Temperature
    chills    = await latest_numeric_value("75326-8")   # Chills (code to label)
    skin      = await latest_numeric_value("39106-0")   # Skin-look (code to label)
    allergy   = await latest_numeric_value("69730-0")   # Allergic-state (code to label)

    # 4. Translate toxicity codes to labels
    chills_map = {0: "None", 1: "Shaking", 2: "Rigor"}
    skin_map   = {0: "Erythema", 1: "Vesiculation", 2: "Desquamation", 3: "Exfoliation"}
    allergy_map= {0: "Edema", 1: "Bronchospasm", 2: "Severe-Bronchospasm", 3: "Anaphylactic-Shock"}

    if chills is not None:
        chills = chills_map.get(int(chills), "Unknown")
    if skin is not None:
        skin = skin_map.get(int(skin), "Unknown")
    if allergy is not None:
        allergy = allergy_map.get(int(allergy), "Unknown")

    # 5. Check for missing data
    if None in (h_value, w_value, fever, chills, skin, allergy):
        return "Insufficient data (need hemoglobin, WBC, and toxicity parameters)."

    # 6. Compute states
    hemo_state = get_hemoglobin_state(gender, h_value)
    hema_state = get_hematological_state(gender, h_value, w_value)
    tox_grade  = get_toxicity_grade(fever, chills, skin, allergy)

    # 7. Lookup recommendation
    treatment = treatment_rules.get(gender, {}).get((hemo_state, hema_state, tox_grade))
    if not treatment:
        return f"No treatment rule found for {hemo_state} + {hema_state} + {tox_grade}"

    return {
        "gender": gender,
        "hemoglobin_value": h_value,
        "wbc_value": w_value,
        "hemoglobin_state": hemo_state,
        "hematological_state": hema_state,
        "toxicity_grade": tox_grade,
        "treatment": treatment
    }

def get_toxicity_grade(fever: float, chills: str, skin_look: str, allergic_state: str) -> str:
    """Returns Grade I–IV based on max severity across symptoms."""

    # Map for output priority
    grade_order = ["Grade I", "Grade II", "Grade III", "Grade IV"]

    max_grade_index = -1

    # Fever rule
    if fever >= 40.0:
        max_grade_index = max(max_grade_index, grade_order.index("Grade IV"))
    elif fever >= 40.0:
        max_grade_index = max(max_grade_index, grade_order.index("Grade III"))
    elif fever >= 38.5:
        max_grade_index = max(max_grade_index, grade_order.index("Grade II"))
    else:
        max_grade_index = max(max_grade_index, grade_order.index("Grade I"))

    # Chills rule
    chills_map = {
        "None": "Grade I",
        "Shaking": "Grade II",
        "Rigor": "Grade III"  # also Grade IV, but since III is enough for max()
    }
    if chills in chills_map:
        max_grade_index = max(max_grade_index, grade_order.index(chills_map[chills]))

    # Skin-look rule
    skin_map = {
        "Erythema": "Grade I",
        "Vesiculation": "Grade II",
        "Desquamation": "Grade III",
        "Exfoliation": "Grade IV"
    }
    if skin_look in skin_map:
        max_grade_index = max(max_grade_index, grade_order.index(skin_map[skin_look]))

    # Allergic-state rule
    allergy_map = {
        "Edema": "Grade I",
        "Bronchospasm": "Grade II",
        "Sever-Bronchospasm": "Grade III",
        "Anaphylactic-Shock": "Grade IV"
    }
    if allergic_state in allergy_map:
        max_grade_index = max(max_grade_index, grade_order.index(allergy_map[allergic_state]))

    return grade_order[max_grade_index] if max_grade_index >= 0 else "Unknown"
