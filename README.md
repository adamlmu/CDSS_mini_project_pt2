# Clinical Decision Support System (CDSS) – Part 2

A temporal clinical decision support system built in Python, supporting inference based on patient data, test observations, and time-dependent reasoning.

---

## Architecture Overview

The system supports clinical decision-making based on four main components:

### 1. Knowledge Base (KB)
- Defined in `L_TableCore.csv`, mapping medical test values to clinical states.
- Handles rules for:
  - Hemoglobin state
  - Hematological state
  - Systemic toxicity
- Depends on patient gender and value ranges.
- Logic implemented in `knowledge_base.py`, triggered from `cli.py`.

### 2. Database (SQLite)
- **File**: `cdss.db` with 3 main tables:
  - `patients`: patient demographics
  - `loinc`: test identifiers and names
  - `observations`: test values with `valid_start`, `valid_end`, `txn_start`, `txn_end`
- Enables temporal queries and inference.

### 3. Inference Engine
- Executed in `cli.py`, combining DB values and KB logic to produce status and treatment.
- Uses valid time ranges to fetch relevant records.
- Determines current states by value, gender, and time.
- Implements rules like:
  ```
  if gender == 'M' and hemoglobin < 9 → Hemoglobin state = Severe Anemia
  ```

### 4. User Interface
- **CLI**: `cli.py` – enables input, test, reasoning, and logic validation.
- **GUI**: `app.py` – built with Tkinter for:
  - Patient management
  - Observation history
  - Retroactive edit/delete
  - Hemoglobin trend analysis
  - Real-time treatment suggestion

---

## Inference Logic

Each clinical rule is time-aware:
- `valid_start`: when observation becomes valid
- `valid_end`: when it expires
- `txn_start`: when it was recorded
- `txn_end`: when it was corrected/expired

Example:
```sql
WHERE valid_start <= T AND (valid_end IS NULL OR valid_end >= T)
```

---

## User Guide

### Setup

```bash
conda env create -f environment.yml
conda activate cdss
python app.py
```

---

## GUI Screens

### 1. Add Patient
- Fields: First name, last name, gender, birth date
- Saves to `patients` table

### 2. Add Observation
- Inputs: Patient ID, LOINC code or name, value, timestamp
- Supports real-time or retroactive entries

### 3. Observation History
- View historical values by patient and test
- Filter by time and test

### 4. Current Status
- Hemoglobin / WBC state at given time
- Based on most recent valid observation

### 5. Retroactive Edit/Delete
- Update or delete past entries by LOINC name or code
- Validity-aware logic with proper commit handling

### 6. Hemoglobin State Intervals
- Analyze hemoglobin states over time window
- Output: value, inferred state, and valid time range

### 7. Treatment Recommendation
- Combines multiple clinical states
- Returns treatment suggestions: medication, tests, follow-up

---

## DSS Feature Support

| Dimension     | Support Level | Notes                                                                 |
|---------------|----------------|-----------------------------------------------------------------------|
| **Time**      | Full           | All queries are temporal using `valid_start`, `valid_end`            |
| **Patient**   | Full           | All logic is per `patient_id`                                        |
| **Problem**   | Full           | Observations mapped to states like anemia or toxicity                |
| **User**      | Basic          | No role-based filtering yet                                          |
| **Recommendation** | Full     | Real-time suggestions based on inference rules                       |
| **Explainability** | Partial  | Shows inferred states but no rule explanation text                   |
| **Intervention** | Full        | Recommendations include medication, tests, monitoring, counseling    |

---

## Example Rule

```python
if gender == "F" and hemoglobin < 8.5:
    hemoglobin_state = "Severe Anemia"
```

---

## GitHub

Clone this repo:

```bash
git clone https://github.com/adamlmu/CDSS_mini_project_pt2.git
```

---

## Notes

> This CDSS system demonstrates full temporal support, flexible data entry, and real-time reasoning capabilities. Improvements may include explainable output and role-based access control.
