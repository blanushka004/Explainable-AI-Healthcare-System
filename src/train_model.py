import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix
)


# ==========================================
# 1. Define project paths
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "data" / "heart_disease.csv"
MODEL_DIR = BASE_DIR / "models"

MODEL_DIR.mkdir(exist_ok=True)


# ==========================================
# 2. Load cleaned dataset
# ==========================================

print("=" * 60)
print("LOADING HEART DISEASE DATASET")
print("=" * 60)

df = pd.read_csv(DATA_FILE)

print("Dataset shape:", df.shape)

print("\nFirst 5 rows:")
print(df.head())


# ==========================================
# 3. Separate features and target
# ==========================================

X = df.drop("target", axis=1)

y = df["target"]


print("\nFeatures:")
print(list(X.columns))

print("\nTarget distribution:")
print(y.value_counts())


# ==========================================
# 4. Split dataset into training and testing
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))


# ==========================================
# 5. Define ML models
# ==========================================

models = {

    "Logistic Regression": Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            max_iter=1000,
            random_state=42
        ))
    ]),

    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced"
    ),

    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    )
}


# ==========================================
# 6. Train and evaluate models
# ==========================================

results = []

best_model = None
best_model_name = None
best_auc = 0


for name, model in models.items():

    print("\n" + "=" * 60)
    print(f"TRAINING: {name}")
    print("=" * 60)

    # Train model
    model.fit(X_train, y_train)

    # Predict classes
    y_pred = model.predict(X_test)

    # Predict probabilities
    y_prob = model.predict_proba(X_test)[:, 1]

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)

    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0
    )

    auc = roc_auc_score(
        y_test,
        y_prob
    )


    # Store results
    results.append({
        "Model": name,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1 Score": f1,
        "ROC-AUC": auc
    })


    # Print results
    print(f"\nAccuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {auc:.4f}")


    # Classification report
    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            y_pred,
            target_names=[
                "No Heart Disease",
                "Heart Disease"
            ],
            zero_division=0
        )
    )


    # Confusion matrix
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))


    # Select best model based on ROC-AUC
    if auc > best_auc:
        best_auc = auc
        best_model = model
        best_model_name = name


# ==========================================
# 7. Compare all models
# ==========================================

results_df = pd.DataFrame(results)

print("\n" + "=" * 60)
print("MODEL COMPARISON")
print("=" * 60)

print(
    results_df.to_string(
        index=False
    )
)


# ==========================================
# 8. Save model comparison results
# ==========================================

results_file = BASE_DIR / "models" / "model_results.csv"

results_df.to_csv(
    results_file,
    index=False
)


# ==========================================
# 9. Save the best model
# ==========================================

best_model_file = MODEL_DIR / "best_model.pkl"

joblib.dump(
    best_model,
    best_model_file
)


# ==========================================
# 10. Save feature names
# ==========================================

feature_file = MODEL_DIR / "feature_names.pkl"

joblib.dump(
    list(X.columns),
    feature_file
)


# ==========================================
# 11. Final output
# ==========================================

print("\n" + "=" * 60)
print("TRAINING COMPLETED SUCCESSFULLY")
print("=" * 60)

print(f"\nBest Model: {best_model_name}")
print(f"Best ROC-AUC: {best_auc:.4f}")

print("\nSaved files:")

print(f"Best model: {best_model_file}")

print(f"Feature names: {feature_file}")

print(f"Model results: {results_file}")