from pathlib import Path
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from model_io import load_bundle,load_metadata
from model_trainer import RacePredictorTrainer,FEATURES
from strategy import scenario_time
FOLDER=Path(__file__).parent;ROOT=FOLDER.resolve().parents[2]
st.set_page_config(page_title='Race Result Predictor',page_icon='📈',layout='wide')
st.markdown('''<style>[data-testid="stAppViewContainer"]{background:#08090a;color:#f7f8f8;font-family:Arial,sans-serif}.stButton>button{background:#d71920;color:white}button:focus-visible{outline:3px solid #00d8ec!important}[data-testid="stMetric"]{background:#151719;padding:12px;border-radius:8px}</style>''',unsafe_allow_html=True)
st.title('Race Result Predictor');st.caption('Historical backtests and transparent strategy scenarios • separate from live race forecasts')
bundle,reason=load_bundle(FOLDER)
meta=bundle['metadata'] if bundle else load_metadata(FOLDER)
if reason:st.warning(reason)
if meta:
    st.caption(f"Data cutoff: {meta['data_cutoff']} • Training 2018–2023 • 2024 selection/calibration • 2025 held-out test")
    st.sidebar.header('Measured held-out results')
    st.sidebar.metric('2025 position MAE',f"{meta['evaluation_2025']['mae']:.3f}")
    st.sidebar.metric('Qualifying baseline MAE',f"{meta['qualifying_order_baseline']['mae']:.3f}")
    st.sidebar.metric('2025 probability Brier',f"{meta['evaluation_2025']['brier_score']:.3f}")
    st.sidebar.metric('Simple probability Brier',f"{meta['simple_probability_baseline']['brier_score']:.3f}")
    st.sidebar.caption('Lower is better. Probability Brier measures squared probability error; MAE is classified-position error.')
forecast,strategy,evaluation=st.tabs(['Full-grid forecast','Strategy what-if','Evaluation & coverage'])
with forecast:
    history_path=ROOT/'data/historical.csv'
    if history_path.exists():
        history=pd.read_csv(history_path);features=RacePredictorTrainer(history).engineer_features(history)
        races=features[['raceId','raceName','season']].drop_duplicates().sort_values('raceId',ascending=False)
        options=races.raceId.tolist();default=202412 if 202412 in options else options[0]
        race=st.selectbox('Historical race / complete classified grid',options,index=options.index(default),format_func=lambda rid:f"{races[races.raceId==rid].iloc[0].season} {races[races.raceId==rid].iloc[0].raceName}")
        data=features[features.raceId==race].sort_values('position_qual')
        grid=data[['driverName','constructorName',*FEATURES]].rename(columns={'driverName':'Driver','constructorName':'Team'}).reset_index(drop=True)
        st.caption(f'{len(grid)} drivers. Prior-race form reconstructs information available before this race; changing inputs is hypothetical. Completed-race outcomes are not forecast inputs.')
    else:
        grid=pd.DataFrame({'Driver':[f'Demo Driver {i:02}' for i in range(1,21)],'Team':[f'Demo Team {(i+1)//2}' for i in range(1,21)],'position_qual':list(range(1,21)),'driver_rolling_perf':[10.5]*20,'team_rolling_perf':[10.5]*20})
        st.info('Historical data unavailable. This complete 20-driver fictional grid is a synthetic demonstration.')
    edited=st.data_editor(grid,hide_index=True,width='stretch',disabled=['Driver','Team'],key=f'grid_{race if history_path.exists() else "demo"}',column_config={f:st.column_config.NumberColumn(f,min_value=1,max_value=30,step=1 if f=='position_qual' else .1) for f in FEATURES})
    st.caption('Position qualifying = rank. Driver form = exponentially weighted previous results, with span 5. Team form = prior five race means after aggregating both teammates. Cold start = 10.5.')
    if st.button('Generate full-grid forecast',type='primary'):
        if edited[FEATURES].isna().any().any() or not np.isfinite(edited[FEATURES].to_numpy()).all():st.error('Every input must be a finite value.')
        else:
            out=edited[['Driver','Team','position_qual']].copy();out['Qualifying baseline order']=edited.position_qual.rank(method='first').astype(int)
            if bundle:
                x=bundle['scaler'].transform(edited[FEATURES]);rank=bundle['rank_model'].predict(x);p=bundle['top10_model'].predict_proba(x)[:,1];p=bundle['calibrator'].predict_proba(np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6))).reshape(-1,1))[:,1]
                out['Model order']=pd.Series(rank,index=out.index).rank(method='first').astype(int);out['Expected classified position']=rank.round(2);out['Top-10 probability (%)']=(p*100).round(1)
                out=out.sort_values('Model order')
            season=int(data.season.iloc[0]) if history_path.exists() else None
            stage='2025 held-out score' if season==2025 else '2024 selection/calibration score' if season==2024 else 'Training-season exploratory score' if season else 'Synthetic demo'
            st.session_state.forecast=out;st.session_state.forecast_label=f"{stage} • {len(out)} drivers • hypothetical if edited"
    if 'forecast' in st.session_state:
        st.subheader('Saved forecast');st.caption(st.session_state.forecast_label);st.dataframe(st.session_state.forecast,hide_index=True,width='stretch');st.download_button('Export forecast CSV',st.session_state.forecast.to_csv(index=False),'forecast.csv')
        st.caption('Model order ranks independent expected-position estimates across this grid. Top-10 probability is a calibrated marginal probability; values are not mutually exclusive and do not sum to 100%. Strategy scenarios below do not modify ML probabilities.')
        with st.expander('Accessible forecast table'):st.table(st.session_state.forecast)
with strategy:
    st.subheader('Strategy scenarios');st.caption('Illustrative constant base pace plus linear per-stint degradation and pit losses. No weather, traffic, safety cars or warm-up model.')
    c1,c2,c3=st.columns(3);laps=int(c1.number_input('Race laps',min_value=5,max_value=100,value=52));pace=c2.number_input('Base lap pace (s)',min_value=30.,max_value=200.,value=90.);loss=c3.slider('Pit loss per stop (s)',min_value=0.,max_value=50.,value=22.,step=.5)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('**One stop**');one=int(st.number_input('One-stop pit lap',min_value=1,max_value=laps-1,value=min(26,laps-1)))
        compound1=st.selectbox('One-stop compounds',['Medium → Hard','Soft → Hard','Hard → Medium'])
        d1=st.number_input('One-stop first stint degradation (s/lap age)',min_value=0.,max_value=2.,value=.10,step=.01);d2=st.number_input('One-stop second stint degradation (s/lap age)',min_value=0.,max_value=2.,value=.08,step=.01)
    with c2:
        st.markdown('**Two stops**');a=int(st.number_input('Two-stop first pit lap',min_value=1,max_value=laps-2,value=min(17,laps-2)));b=int(st.number_input('Two-stop second pit lap',min_value=a+1,max_value=laps-1,value=max(a+1,min(35,laps-1))))
        compound2=st.selectbox('Two-stop compounds',['Soft → Medium → Soft','Medium → Hard → Soft'])
        e1=st.number_input('Two-stop first degradation (s/lap age)',min_value=0.,max_value=2.,value=.10,step=.01);e2=st.number_input('Two-stop second degradation (s/lap age)',min_value=0.,max_value=2.,value=.08,step=.01);e3=st.number_input('Two-stop third degradation (s/lap age)',min_value=0.,max_value=2.,value=.10,step=.01)
    first=scenario_time(laps,pace,[one],loss,[d1,d2]);second=scenario_time(laps,pace,[a,b],loss,[e1,e2,e3]);c1,c2,c3=st.columns(3)
    c1.metric('One-stop scenario time',f"{first['total_seconds']:.1f} s");c2.metric('Two-stop scenario time',f"{second['total_seconds']:.1f} s");c3.metric('Two − one stop',f"{second['total_seconds']-first['total_seconds']:+.1f} s")
    st.caption(f'Compounds are labels; pace and degradation are the displayed user assumptions: {compound1}; {compound2}. Stint lap time = base pace + degradation × tyre age starting at zero; pit cost = stops × pit loss.')
    st.dataframe(pd.DataFrame([{'Scenario':name,**s} for name,result in [('One stop',first),('Two stops',second)] for s in result['stints']]),hide_index=True,width='stretch')
with evaluation:
    if meta:
        st.json(meta);st.caption('All performance numbers are loaded from the saved evaluation artifact. The 2025 test set was evaluated after model selection and calibration without fitting on its outcomes.')
        st.download_button('Download model metadata',json.dumps(meta,indent=2),'model-metadata.json')
    else:st.info('No evaluated historical artifact yet. Old unversioned model files are synthetic demonstrations and are not used as historical forecasts.')
