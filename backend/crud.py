from sqlalchemy.orm import Session

from . import models, schemas


def create_prediction(
    db: Session,
    prediction_data: schemas.PredictionCreate
):
    db_prediction = models.Prediction(
        **prediction_data.model_dump()
    )

    try:
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)
    except Exception:
        db.rollback()
        raise

    return db_prediction
def get_predictions(
    db: Session,
    skip: int = 0,
    limit: int = 100
):
    return (
        db.query(models.Prediction)
        .order_by(models.Prediction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_prediction_by_id(
    db: Session,
    prediction_id: int
):
    return (
        db.query(models.Prediction)
        .filter(
            models.Prediction.id == prediction_id
        )
        .first()
    )
