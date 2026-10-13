"""Historical chronological training; preprocessing sees training rows only."""
from pathlib import Path
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor,GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error,brier_score_loss
import joblib
FEATURES=['position_qual','driver_rolling_perf','team_rolling_perf']
class RacePredictorTrainer:
    def __init__(self,data):self.data=data;self.scaler=StandardScaler();self.model_rank=None;self.model_top10=None;self.calibrator=None
    def engineer_features(self,df):
        df=df.sort_values(['season','raceId','driverId']).copy()
        df['driver_rolling_perf']=df.groupby('driverId').position_res.transform(lambda x:x.shift(1).ewm(span=5,adjust=False).mean()).fillna(10.5)
        team=df.groupby(['season','raceId','constructorId'],as_index=False).position_res.mean().sort_values(['season','raceId'])
        team['team_rolling_perf']=team.groupby('constructorId').position_res.transform(lambda x:x.shift(1).ewm(span=5,adjust=False).mean()).fillna(10.5)
        df=df.merge(team[['season','raceId','constructorId','team_rolling_perf']],on=['season','raceId','constructorId'],validate='many_to_one')
        df['is_top10']=(df.position_res<=10).astype(int);return df
    def split_data(self,df):return df[df.season.between(2018,2023)],df[df.season==2024],df[df.season==2025]
    def train(self,train_df,n_estimators=100,max_depth=2):
        x=self.scaler.fit_transform(train_df[FEATURES]);self.model_rank=GradientBoostingRegressor(n_estimators=n_estimators,max_depth=max_depth,random_state=42).fit(x,train_df.position_res);self.model_top10=GradientBoostingClassifier(n_estimators=n_estimators,max_depth=max_depth,random_state=42).fit(x,train_df.is_top10)
    def predict(self,df):
        x=self.scaler.transform(df[FEATURES]);r=self.model_rank.predict(x);p=self.model_top10.predict_proba(x)[:,1]
        if self.calibrator is not None:p=self.calibrator.predict_proba(np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6))).reshape(-1,1))[:,1]
        return r,p
    def evaluate(self,df):
        r,p=self.predict(df);return {'mae':float(mean_absolute_error(df.position_res,r)),'brier_score':float(brier_score_loss(df.is_top10,p)),'rows':len(df),'races':int(df.raceId.nunique())}
    def run(self,folder):
        df=self.engineer_features(self.data);train,selection,test=self.split_data(df)
        if any(x.empty for x in (train,selection,test)):raise ValueError('Need complete 2018–2023, 2024 and 2025 datasets.')
        rounds=sorted(selection.raceId.unique());select=selection[selection.raceId.isin(rounds[:len(rounds)//2])];calibration=selection[selection.raceId.isin(rounds[len(rounds)//2:])]
        candidates=[]
        for depth in (2,3):
            self.train(train,max_depth=depth);candidates.append((self.evaluate(select)['mae'],depth))
        depth=min(candidates)[1];self.train(train,max_depth=depth)
        x=self.scaler.transform(calibration[FEATURES]);prob=self.model_top10.predict_proba(x)[:,1];logit=np.log(np.clip(prob,1e-6,1-1e-6)/(1-np.clip(prob,1e-6,1-1e-6))).reshape(-1,1)
        self.calibrator=LogisticRegression(random_state=42).fit(logit,calibration.is_top10)
        # Simple probability baseline: empirical qualifying-position bins from TRAINING only.
        bins=pd.cut(train.position_qual,[-1,5,10,15,100],labels=False)
        base=train.groupby(bins).is_top10.mean().to_dict();testbin=pd.cut(test.position_qual,[-1,5,10,15,100],labels=False);baseline_prob=testbin.map(base).fillna(train.is_top10.mean()).to_numpy()
        metadata={'schema_version':1,'mode':'historical','source':'Jolpica F1','source_url':'https://api.jolpi.ca/ergast/f1/','trained_at':datetime.now(timezone.utc).isoformat(),'training_seasons':[2018,2023],'selection_season':2024,'selection_rounds':len(rounds)//2,'calibration_rounds':len(rounds)-len(rounds)//2,'test_season':2025,'data_cutoff':str(df.date.max()),'training_rows':len(train),'features':FEATURES,'feature_definitions':{'position_qual':'Qualifying rank; missing qualifying falls back to grid, or 20 for no grid','driver_rolling_perf':'Mean classified finish in previous five completed races; 10.5 cold start','team_rolling_perf':'Mean of both classified teammate finishes per race, then previous five completed team races; 10.5 cold start'},'target':'Classified finishing position, including retired drivers; not elapsed race time','model':f'Gradient Boosting, 100 estimators, depth {depth}; Platt probability calibration on latter 2024 races','evaluation_2025':self.evaluate(test),'qualifying_order_baseline':{'mae':float(mean_absolute_error(test.position_res,test.position_qual))},'simple_probability_baseline':{'brier_score':float(brier_score_loss(test.is_top10,baseline_prob)),'qualifying_bins':{str(k):float(v) for k,v in base.items()}},'limitations':['Historical backtest; no proof of future predictive accuracy','No weather, incidents, pit strategy or circuit features in ML','Missing qualifying uses a labelled grid fallback','No model selection on held-out 2025 results']}
        folder=Path(folder);folder.mkdir(exist_ok=True)
        for name,obj in [('rank_model',self.model_rank),('top10_model',self.model_top10),('scaler',self.scaler),('calibrator',self.calibrator)]:joblib.dump(obj,folder/(name+'.pkl'))
        (folder/'model_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');df.to_csv(folder/'features.csv',index=False);return metadata
if __name__=='__main__':
    root=Path(__file__).resolve().parents[3];data=pd.read_csv(root/'data/historical.csv');print(json.dumps(RacePredictorTrainer(data).run(Path(__file__).parent),indent=2))
