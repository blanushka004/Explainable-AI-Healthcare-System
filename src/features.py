"""One feature contract shared by training, inference, validation and the UI."""
FEATURES = {
    "age": {"label": "Age", "unit": "years", "min": 18, "max": 100, "default": 54},
    "sex": {"label": "Sex (dataset coding)", "options": {0: "Female", 1: "Male"}, "default": 1},
    "cp": {"label": "Chest pain type", "options": {1: "Typical angina", 2: "Atypical angina", 3: "Non-anginal pain", 4: "Asymptomatic"}, "default": 2},
    "trestbps": {"label": "Resting blood pressure", "unit": "mm Hg", "min": 70, "max": 250, "default": 130},
    "chol": {"label": "Serum cholesterol", "unit": "mg/dL", "min": 100, "max": 600, "default": 240},
    "fbs": {"label": "Fasting blood sugar > 120 mg/dL", "options": {0: "No", 1: "Yes"}, "default": 0},
    "restecg": {"label": "Resting ECG", "options": {0: "Normal", 1: "ST-T wave abnormality", 2: "Probable/definite LV hypertrophy"}, "default": 0},
    "thalach": {"label": "Maximum achieved heart rate", "unit": "bpm", "min": 40, "max": 250, "default": 150},
    "exang": {"label": "Exercise-induced angina", "options": {0: "No", 1: "Yes"}, "default": 0},
    "oldpeak": {"label": "Exercise ST depression", "unit": "relative to rest", "min": 0, "max": 10, "step": 0.1, "default": 1.0},
    "slope": {"label": "Peak exercise ST slope", "options": {1: "Upsloping", 2: "Flat", 3: "Downsloping"}, "default": 2},
    "ca": {"label": "Major vessels colored by fluoroscopy", "options": {0: "0", 1: "1", 2: "2", 3: "3"}, "default": 0},
    "thal": {"label": "Thallium stress-test result", "options": {3: "Normal", 6: "Fixed defect", 7: "Reversible defect"}, "default": 3},
}
FEATURE_ORDER = list(FEATURES)
CATEGORICAL = [k for k,v in FEATURES.items() if "options" in v]
NUMERIC = [k for k in FEATURE_ORDER if k not in CATEGORICAL]
