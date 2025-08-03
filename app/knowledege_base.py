# app/knowledge_base.py

hemoglobin_state = {
    "Male": [
        (0, 9, "Severe Anemia"),
        (9, 11, "Moderate Anemia"),
        (11, 13, "Mild Anemia"),
        (13, 16, "Normal Hemoglobin"),
        (16, float("inf"), "Polyhemia")
    ],
    "Female": [
        (0, 8, "Severe Anemia"),
        (8, 10, "Moderate Anemia"),
        (10, 12, "Mild Anemia"),
        (12, 14, "Normal Hemoglobin"),
        (14, float("inf"), "Polycytemia")
    ]
}

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

treatment_rules = {
    "Male": {
        ("Severe Anemia", "Pancytopenia"): ["GRADE I", "Measure BP once a week"],
        ("Moderate Anemia", "Anemia"): ["GRADE II", "Measure BP every 3 days", "Give aspirin 5g twice a week"],
        ("Mild Anemia", "Suspected Leukemia"): ["GRADE III", "Measure BP every day", "Give aspirin 15g every day", "Diet consultation"],
        ("Normal Hemoglobin", "Leukemoid reaction"): ["GRADE IV", "Measure BP twice a day", "Give aspirin 15g every day", "Exercise consultation", "Diet consultation"],
        ("Polyhemia", "Suspected Polycytemia Vera"): ["GRADE IV", "Measure BP every hour", "Give 1 gr magnesium every hour", "Exercise consultation", "Call family"]
    },
    "Female": {
        ("Severe Anemia", "Pancytopenia"): ["GRADE I", "Measure BP every 3 days"],
        ("Moderate Anemia", "Anemia"): ["GRADE II", "Measure BP every 3 days", "Give Celectone 2g twice a day for two days"],
        ("Mild Anemia", "Suspected Leukemia"): ["GRADE III", "Measure BP every day", "Give 1 gr magnesium every 3 hours", "Diet consultation"],
        ("Normal Hemoglobin", "Leukemoid reaction"): ["GRADE IV", "Measure BP twice a day", "Give 1 gr magnesium every hour", "Exercise consultation", "Diet consultation"],
        ("Polyhemia", "Suspected Polycytemia Vera"): ["GRADE IV", "Measure BP every hour", "Give 1 gr magnesium every hour", "Exercise consultation", "Call help"]
    }
}
