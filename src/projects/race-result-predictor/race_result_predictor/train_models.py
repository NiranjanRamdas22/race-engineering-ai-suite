"""Train historical models only; synthetic artifacts are never labelled as evaluated."""
from pathlib import Path
import pandas as pd,json
from model_trainer import RacePredictorTrainer
if __name__=='__main__':
    folder=Path(__file__).parent;root=folder.resolve().parents[2]
    print(json.dumps(RacePredictorTrainer(pd.read_csv(root/'data/historical.csv')).run(folder),indent=2))
