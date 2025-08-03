# app/knowledge_base.py

import pandas as pd

# Hemoglobin state based on gender and level, with Good-Before and Good-After (in days)
hemoglobin_state = {
    "Male": [
        (0, 9, "Severe Anemia", 2, 5),
        (9, 11, "Moderate Anemia", 2, 4),
        (11, 13, "Mild Anemia", 1, 3),
        (13, 16, "Normal Hemoglobin", 1, 2),
        (16, float("inf"), "Polyhemia", 1, 1)
    ],
    "Female": [
        (0, 8, "Severe Anemia", 2, 5),
        (8, 10, "Moderate Anemia", 2, 4),
        (10, 12, "Mild Anemia", 1, 3),
        (12, 14, "Normal Hemoglobin", 1, 2),
        (14, float("inf"), "Suspected Polycytemia Vera", 1, 1)
    ]
}

def get_hemoglobin_state_with_timing(gender: str, value: float):
    for low, high, label, good_before, good_after in hemoglobin_state[gender]:
        if low <= value < high:
            return {
                "state": label,
                "good_before": pd.Timedelta(days=good_before),
                "good_after": pd.Timedelta(days=good_after)
            }
    return {
        "state": "Unknown",
        "good_before": pd.Timedelta(days=0),
        "good_after": pd.Timedelta(days=0)
    }

# Hematological state based on gender, hemoglobin level, and WBC level
hematological_state = {
    "Male": {
        (0, 13): {
            (0, 4000): "Pancytopenia",
            (4000, 10000): "Anemia",
            (10000, float("inf")): "Suspected Leukemia"
        },
        (13, 16): {
            (0, 4000): "Leukopenia",
            (4000, 10000): "Normal",
            (10000, float("inf")): "Leukemoid reaction"
        },
        (16, float("inf")): {
            (0, 4000): "Suspected Polycytemia Vera",
            (4000, 10000): "Polyhemia",
            (10000, float("inf")): "Suspected Polycytemia Vera"
        }
    },
    "Female": {
        (0, 12): {
            (0, 4000): "Pancytopenia",
            (4000, 10000): "Anemia",
            (10000, float("inf")): "Suspected Leukemia"
        },
        (12, 14): {
            (0, 4000): "Leukopenia",
            (4000, 10000): "Normal",
            (10000, float("inf")): "Leukemoid reaction"
        },
        (14, float("inf")): {
            (0, 4000): "Suspected Polycytemia Vera",
            (4000, 10000): "Polyhemia",
            (10000, float("inf")): "Suspected Polycytemia Vera"
        }
    }
}

# Treatment rules based on gender, hemoglobin state, and hematological state
treatment_rules = {
    "Male": {
        ("Severe Anemia", "Pancytopenia", "Grade I"): [
            "Measure BP once a week"
        ],
        ("Moderate Anemia", "Anemia", "Grade II"): [
            "Measure BP every 3 days",
            "Give aspirin 5g twice a week"
        ],
        ("Mild Anemia", "Suspected Leukemia", "Grade III"): [
            "Measure BP every day",
            "Give aspirin 15g every day",
            "Diet consultation"
        ],
        ("Normal Hemoglobin", "Leukemoid reaction", "Grade IV"): [
            "Measure BP twice a day",
            "Give aspirin 15g every day",
            "Exercise consultation",
            "Diet consultation"
        ],
        ("Polyhemia", "Suspected Polycytemia Vera", "Grade IV"): [
            "Measure BP every hour",
            "Give 1 gr magnesium every hour",
            "Exercise consultation",
            "Call family"
        ],
    },
    "Female": {
        ("Severe Anemia", "Pancytopenia", "Grade I"): [
            "Measure BP every 3 days"
        ],
        ("Moderate Anemia", "Anemia", "Grade II"): [
            "Measure BP every 3 days",
            "Give Celectone 2g twice a day for two days drug treatment"
        ],
        ("Mild Anemia", "Suspected Leukemia", "Grade III"): [
            "Measure BP every day",
            "Give 1 gr magnesium every 3 hours",
            "Diet consultation"
        ],
        ("Normal Hemoglobin", "Leukemoid reaction", "Grade IV"): [
            "Measure BP twice a day",
            "Give 1 gr magnesium every hour",
            "Exercise consultation",
            "Diet consultation"
        ],
        ("Polyhemia", "Suspected Polycytemia Vera", "Grade IV"): [
            "Measure BP every hour",
            "Give 1 gr magnesium every hour",
            "Exercise consultation",
            "Call help"
        ]
    }
}

# Systemic toxicity grading rules (Maximal OR table)
toxicity_rules = {
    "Allergic-state": {
        "Grade I": ["Edema"],
        "Grade II": ["Bronchospasm"],
        "Grade III": ["Sever-Bronchospasm"],
        "Grade IV": ["Anaphylactic-Shock"]
    },
    "Chills": {
        "Grade I": ["None"],
        "Grade II": ["Shaking"],
        "Grade III": ["Rigor"],
        "Grade IV": ["Rigor"]
    },
    "Fever": {
        "Grade I": (0, 38.5),
        "Grade II": (38.5, 40.0),
        "Grade III": (40.0, float("inf"))
    },
    "Skin-look": {
        "Grade I": ["Erythema"],
        "Grade II": ["Vesiculation"],
        "Grade III": ["Desquamation"],
        "Grade IV": ["Exfoliation"]
    }
}

def get_toxicity_grade_from_features(fever=None, chills=None, skin=None, allergy=None):
    """
    Given observations for toxicity parameters, return the maximal grade (I-IV).
    """
    value_to_grade = {
        # Fever
        "fever": lambda v: (
            "GRADE I" if v <= 38.5 else
            "GRADE II" if v <= 40.0 else
            "GRADE III"
        ),
        # Chills
        "chills": {
            "None": "GRADE I",
            "Shaking": "GRADE II",
            "Rigor": "GRADE III"
        },
        # Skin-look
        "skin": {
            "Erythema": "GRADE I",
            "Vesiculation": "GRADE II",
            "Desquamation": "GRADE III",
            "Exfoliation": "GRADE IV"
        },
        # Allergy
        "allergy": {
            "Edema": "GRADE I",
            "Bronchospasm": "GRADE II",
            "Sever-Bronchospasm": "GRADE III",
            "Anaphylactic-Shock": "GRADE IV"
        }
    }

    grades = []

    if isinstance(fever, (int, float)):
        grades.append(value_to_grade["fever"](fever))

    if chills in value_to_grade["chills"]:
        grades.append(value_to_grade["chills"][chills])

    if skin in value_to_grade["skin"]:
        grades.append(value_to_grade["skin"][skin])

    if allergy in value_to_grade["allergy"]:
        grades.append(value_to_grade["allergy"][allergy])

    # Sort GRADE I → GRADE IV
    grade_order = {"GRADE I": 1, "GRADE II": 2, "GRADE III": 3, "GRADE IV": 4}
    if not grades:
        return "GRADE I"  # default

    max_grade = max(grades, key=lambda g: grade_order.get(g, 0))
    return max_grade
