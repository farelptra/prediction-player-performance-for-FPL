from __future__ import annotations
import os
import argparse
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.ml.train import train_and_save

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["train"])
    args = parser.parse_args()

    model_dir = os.getenv("MODEL_DIR", "./models_store")
    model_version = os.getenv("MODEL_VERSION", "rf_v1")

    db: Session = SessionLocal()
    try:
        if args.cmd == "train":
            report = train_and_save(db, model_dir=model_dir, model_version=model_version)
            print("TRAIN DONE")
            print(report)
    finally:
        db.close()

if __name__ == "__main__":
    main()
