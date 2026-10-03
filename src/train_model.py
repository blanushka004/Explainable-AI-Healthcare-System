"""Reproducible training. Run from the project root: python -m src.train_model."""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.inspection import permutation_importance
from src.features import FEATURE_ORDER, NUMERIC, CATEGORICAL, FEATURES
from src.metrics import metrics, curves, bootstrap_intervals

ROOT=Path(__file__).resolve().parents[1]


def train(seed=42):
    source=ROOT/"data/heart_disease.csv"
    df=pd.read_csv(source)
    required=FEATURE_ORDER+["target"]
    if set(df.columns)!=set(required): raise ValueError("Unexpected dataset schema")
    if not set(df.target.unique()).issubset({0,1}): raise ValueError("Target must be binary")
    raw_n=len(df)
    duplicates=int(df.duplicated().sum())
    df=df.drop_duplicates().reset_index(drop=True)
    if df[required].isna().any().any(): raise ValueError("Use the cleaned dataset: missing values found")
    X,y=df[FEATURE_ORDER],df.target.astype(int)
    train_ids,test_ids=train_test_split(np.arange(len(df)),test_size=.2,stratify=y,random_state=seed)
    Xtr,Xte=X.iloc[train_ids],X.iloc[test_ids]
    ytr,yte=y.iloc[train_ids],y.iloc[test_ids]
    pre=ColumnTransformer([
      ("numeric",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),NUMERIC),
      ("category",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),
         ("encode",OneHotEncoder(categories=[list(FEATURES[k]["options"]) for k in CATEGORICAL],handle_unknown="error",sparse_output=False))]),CATEGORICAL)])
    candidates={
      "Logistic Regression":LogisticRegression(max_iter=2000,random_state=seed),
      "Random Forest":RandomForestClassifier(n_estimators=180,min_samples_leaf=3,class_weight="balanced",random_state=seed,n_jobs=1),
      "Gradient Boosting":GradientBoostingClassifier(n_estimators=100,max_depth=2,learning_rate=.05,random_state=seed)}
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=seed)
    fitted,rows,oof={},{},{}
    for name,estimator in candidates.items():
        print("Training",name,flush=True)
        pipeline=Pipeline([("preprocess",clone(pre)),("model",estimator)])
        p=cross_val_predict(pipeline,Xtr,ytr,cv=cv,method="predict_proba",n_jobs=1)[:,1]
        fold_metrics=[metrics(ytr.iloc[v],p[v]) for _,v in cv.split(Xtr,ytr)]
        rows[name]={"cv":metrics(ytr,p),"cv_roc_auc_mean":float(np.mean([m["roc_auc"] for m in fold_metrics])),
                    "cv_roc_auc_std":float(np.std([m["roc_auc"] for m in fold_metrics])),"fold_metrics":fold_metrics}
        fitted[name]=pipeline.fit(Xtr,ytr);oof[name]=p
    winner=max(rows,key=lambda k:rows[k]["cv_roc_auc_mean"])
    print("Training-only CV winner:",winner,flush=True)
    calibrated=CalibratedClassifierCV(clone(fitted[winner]),method="sigmoid",cv=StratifiedKFold(3,shuffle=True,random_state=seed))
    cal_oof=cross_val_predict(calibrated,Xtr,ytr,cv=cv,method="predict_proba",n_jobs=1)[:,1]
    use_calibration=metrics(ytr,cal_oof)["brier"] < metrics(ytr,oof[winner])["brier"]
    active=calibrated.fit(Xtr,ytr) if use_calibration else fitted[winner]
    active_oof=cal_oof if use_calibration else oof[winner]
    test_p=active.predict_proba(Xte)[:,1]
    artifact_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+hashlib.sha256(source.read_bytes()).hexdigest()[:8]
    thresholds=[metrics(ytr,active_oof,t) for t in np.linspace(.05,.95,91)]
    # An exploratory recall target, not a clinically validated operating point.
    eligible=[m for m in thresholds if m["recall"]>=.9]
    recall_threshold=max(eligible,key=lambda m:m["threshold"])["threshold"] if eligible else None
    for name in fitted:
        p=fitted[name].predict_proba(Xte)[:,1]
        rows[name]["test"]=metrics(yte,p)
    global_importance=permutation_importance(active,Xte,yte,scoring="roc_auc",n_repeats=12,random_state=seed,n_jobs=1)
    importance=sorted([{"feature":k,"mean":float(global_importance.importances_mean[i]),
                        "std":float(global_importance.importances_std[i])} for i,k in enumerate(FEATURE_ORDER)],key=lambda x:x["mean"],reverse=True)
    subgroups=[]
    for label,mask in [("Female",Xte.sex==0),("Male",Xte.sex==1),("Age < 55",Xte.age<55),("Age ≥ 55",Xte.age>=55)]:
        if not mask.any(): continue
        m=metrics(yte[mask],test_p[mask]);m.update(group=label,small_sample=len(yte[mask])<30)
        subgroups.append(m)
    examples=[]
    for i,(idx,row) in enumerate(Xte.iterrows()):
        pred=int(test_p[i]>=.5);actual=int(yte.loc[idx])
        examples.append({"row_id":int(idx),"features":row.to_dict(),"actual":actual,"probability":float(test_p[i]),
                         "outcome":("TP" if actual else "FP") if pred else ("FN" if actual else "TN")})
    report={"version":artifact_id,"created_at":datetime.now(timezone.utc).isoformat(),"seed":seed,
      "dataset":{"name":"UCI Cleveland (complete cases)","source":"https://archive.ics.uci.edu/dataset/45/heart+disease",
        "raw_rows":raw_n,"rows":len(df),"duplicates_removed":duplicates,"missing_values":int(df.isna().sum().sum()),
        "train_count":len(Xtr),"test_count":len(Xte),"positive_count":int(y.sum()),"negative_count":int((1-y).sum()),
        "sha256":hashlib.sha256(source.read_bytes()).hexdigest()},
      "selected_model":winner,"calibrated":use_calibration,"calibration_selection":{"uncalibrated_oof_brier":metrics(ytr,oof[winner])["brier"],"calibrated_oof_brier":metrics(ytr,cal_oof)["brier"]},
      "selection":"Highest mean 5-fold training CV ROC-AUC; sigmoid calibration accepted only if nested OOF Brier improves. Test data is not used for selection.",
      "evaluation_caveat":"The historical project already inspected this test split. This is a reproducible internal benchmark, not a fresh independent external validation.",
      "candidates":rows,"active_cv":metrics(ytr,active_oof),"active_test":metrics(yte,test_p),
      "test_intervals":bootstrap_intervals(yte,test_p,seed),"curves":curves(yte,test_p),
      "thresholds":thresholds,"exploratory_recall_90_threshold":recall_threshold,
      "global_importance":importance,"subgroups":subgroups,"test_cases":examples,
      "feature_statistics":{k:{"min":float(Xtr[k].min()),"max":float(Xtr[k].max()),"median":float(Xtr[k].median()),"q05":float(Xtr[k].quantile(.05)),"q95":float(Xtr[k].quantile(.95))} for k in FEATURE_ORDER},
      "environment":{"python":platform.python_version(),"scikit_learn":sklearn.__version__,"numpy":np.__version__,"pandas":pd.__version__},
      "limitations":["297 complete-case records before deduplication; small single-source historical dataset.",
       "Predicts the dataset disease-presence label; not future events, disease severity, or a diagnosis.",
       "OOF scores used for selection can be optimistic; final internal test metrics and uncertainty are reported separately.",
       "Bootstrap intervals describe sampling uncertainty on this test split, not transportability.",
       "Subgroup metrics are exploratory and do not establish fairness.",
       "Permutation importance uses test data for post-hoc interpretation, never model selection."]}
    destination=ROOT/"models/versions"/artifact_id;destination.mkdir(parents=True,exist_ok=True)
    bundle={"version":artifact_id,"model":active,"candidates":fitted,"features":FEATURE_ORDER,
            "train_X":Xtr.reset_index(drop=True),"train_y":ytr.reset_index(drop=True),
            "train_ids":train_ids.tolist(),"test_ids":test_ids.tolist(),
            "background":Xtr.sample(min(32,len(Xtr)),random_state=seed).reset_index(drop=True),
            "oof_y":ytr.to_numpy(),"oof_probability":active_oof,"report":report}
    joblib.dump(bundle,destination/"bundle.joblib")
    (destination/"evaluation.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    # Publish pointer last: incomplete training never replaces the active version.
    pointer=ROOT/"models/active.json";temporary=pointer.with_suffix(".tmp")
    temporary.write_text(json.dumps({"version":artifact_id}),encoding="utf-8");temporary.replace(pointer)
    joblib.dump(active,ROOT/"models/best_model.pkl")
    joblib.dump(FEATURE_ORDER,ROOT/"models/feature_names.pkl")
    pd.DataFrame([{"Model":name,**r["test"]} for name,r in rows.items()]).drop(columns="confusion_matrix").to_csv(ROOT/"models/model_results.csv",index=False)
    print(json.dumps({"version":artifact_id,"selected_model":winner,"calibrated":use_calibration,"test":report["active_test"]},indent=2))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--seed",type=int,default=42)
    train(parser.parse_args().seed)
