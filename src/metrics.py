import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, brier_score_loss,
                             confusion_matrix, roc_curve, precision_recall_curve)
from sklearn.calibration import calibration_curve


def metrics(y, p, threshold=0.5):
    y, p = np.asarray(y), np.asarray(p)
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(n=len(y), threshold=float(threshold), accuracy=float(accuracy_score(y,pred)),
                precision=float(precision_score(y,pred,zero_division=0)),
                recall=float(recall_score(y,pred,zero_division=0)),
                specificity=float(tn/(tn+fp)) if tn+fp else None,
                f1=float(f1_score(y,pred,zero_division=0)),
                roc_auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
                average_precision=float(average_precision_score(y,p)) if len(np.unique(y))==2 else None,
                brier=float(brier_score_loss(y,p)), confusion_matrix=[[int(tn),int(fp)],[int(fn),int(tp)]])


def curves(y,p):
    fpr,tpr,_ = roc_curve(y,p)
    precision,recall,_ = precision_recall_curve(y,p)
    observed,predicted = calibration_curve(y,p,n_bins=6,strategy="quantile")
    return dict(roc={"x":fpr.tolist(),"y":tpr.tolist()},
                precision_recall={"x":recall.tolist(),"y":precision.tolist()},
                calibration={"x":predicted.tolist(),"y":observed.tolist()})


def bootstrap_intervals(y,p,seed=42,repeats=500):
    y,p=np.asarray(y),np.asarray(p)
    rng=np.random.default_rng(seed)
    scores={k:[] for k in ["accuracy","recall","roc_auc","brier"]}
    for _ in range(repeats):
        i=rng.integers(0,len(y),len(y))
        if len(np.unique(y[i]))<2: continue
        m=metrics(y[i],p[i])
        for k in scores: scores[k].append(m[k])
    return {k:{"low":float(np.quantile(v,.025)),"high":float(np.quantile(v,.975))} for k,v in scores.items()}
