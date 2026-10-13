from pathlib import Path
import fastf1
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analytics import valid_laps,align_laps,seconds_delta,corner_comparison,degradation

st.set_page_config(page_title='F1 Telemetry Lab',page_icon='🏎️',layout='wide')
st.markdown('''<style>html,body,[data-testid="stAppViewContainer"]{background:#08090a;color:#f7f8f8;font-family:Arial,sans-serif}button:focus-visible{outline:3px solid #00d8ec!important}.stButton>button{background:#d71920;color:white}[data-testid="stMetric"]{background:#151719;padding:12px;border-radius:8px}@media(prefers-reduced-motion:reduce){*{transition:none!important}}</style>''',unsafe_allow_html=True)
cache=Path(__file__).parent/'f1_cache';cache.mkdir(exist_ok=True);fastf1.Cache.enable_cache(str(cache))
st.title('F1 Telemetry Lab')
st.caption('Official session telemetry • distance-aligned lap comparison • approximate FastF1 circuit markers')
@st.cache_resource(show_spinner=False)
def load_session(y,g,s):
    session=fastf1.get_session(y,g,s);session.load();return session
st.sidebar.header('Session')
year=st.sidebar.selectbox('Season',[2024,2025,2023,2022])
gp=st.sidebar.selectbox('Circuit',['Silverstone','Monza','Spa','Monaco','Zandvoort','Suzuka'])
kind=st.sidebar.selectbox('Session type',['Q','R','FP1','FP2','FP3','S'])
session=None
try:
    with st.spinner('Loading session; downloaded data is cached for later use…'):session=load_session(year,gp,kind)
except Exception as exc:
    st.warning(f'Session unavailable: {exc}. Choose a cached session or retry.')
    st.sidebar.button('Retry session',on_click=st.cache_resource.clear)
if session is not None:
    drivers=[d for d in session.drivers if len(valid_laps(session.laps.pick_drivers(d)))]
    def driver_name(d):
        r=session.get_driver(d);return f"{r.get('FullName',d)} ({r.get('Abbreviation',d)})"
    if drivers:
        d1=st.sidebar.selectbox('Primary driver',drivers,format_func=driver_name)
        d2=st.sidebar.selectbox('Comparison driver',drivers,index=min(1,len(drivers)-1),format_func=driver_name)
        choices=[]
        for n,d in enumerate([d1,d2],1):
            laps=valid_laps(session.laps.pick_drivers(d))
            number=st.sidebar.selectbox(f'{driver_name(d)} lap (fastest valid first)',laps.LapNumber.astype(int).tolist(),key=f'lap{n}')
            choices.append(laps[laps.LapNumber==number].iloc[0])
        if st.sidebar.button('Analyse selected laps',type='primary'):
            try:
                lap1,lap2=choices
                with st.spinner('Aligning telemetry and circuit markers…'):
                    aligned=align_laps(lap1.get_telemetry().add_distance(),lap2.get_telemetry().add_distance())
                    circuit=session.get_circuit_info()
                    if circuit is not None:circuit.add_marker_distance(lap1)
                    corners=corner_comparison(aligned,circuit.corners if circuit else None)
                    pace=pd.DataFrame(session.laps).copy()
                    pace['Session minutes']=pace.Time.dt.total_seconds()/60;pace['Lap seconds']=pace.LapTime.dt.total_seconds();pace['Rainfall']=pd.Series([None]*len(pace),index=pace.index,dtype=object)
                    weather=session.weather_data
                    if not weather.empty and 'Rainfall' in weather:
                        wt=weather.Time.dt.total_seconds().to_numpy()
                        for idx,row in pace.iterrows():
                            if pd.notna(row.Time):pace.loc[idx,'Rainfall']=bool(weather.iloc[np.abs(wt-row.Time.total_seconds()).argmin()].Rainfall)
                    st.session_state.result={'title':f'{year} {gp} {kind}','names':[driver_name(d1),driver_name(d2)],'laps':[lap1,lap2],'aligned':aligned,'corners':corners,'pace':pace,'kind':kind}
            except Exception as exc:st.error(f'Analysis unavailable: {exc}. Your last successful comparison is retained.')
    else:st.info('No complete, accurate laps available. Choose another session.')
result=st.session_state.get('result')
if not result:st.info('Choose two drivers and complete laps, then select Analyse. Each driver defaults to their fastest valid lap.')
else:
    a=result['aligned'];laps=result['laps'];names=result['names'];table=result['corners']
    st.subheader(result['title']);st.caption(f"Saved comparison: {names[0]} lap {int(laps[0].LapNumber)} vs {names[1]} lap {int(laps[1].LapNumber)}. Analyse again to update.")
    cols=st.columns(3);gap=seconds_delta(laps[0].LapTime,laps[1].LapTime)
    cols[0].metric('Lap delta: primary − comparison',f'{gap:+.3f} s' if gap is not None else 'Unavailable')
    cols[1].metric('Telemetry end delta',f'{a.Delta.iloc[-1]:+.3f} s');cols[2].metric('Overlap',f'{a.Distance.iloc[0]:.0f}–{a.Distance.iloc[-1]:.0f} m')
    st.caption('Official lap delta uses timing-line lap times. Telemetry delta covers the shared distance interval and may differ because endpoints and integrated distances differ.')
    choices=['Full lap']+table.Corner.tolist() if not table.empty else ['Full lap']
    rows=st.session_state.get('cornertable',{}).get('selection',{}).get('rows',[])
    if rows and rows!=st.session_state.get('last_corner_rows') and rows[0]<len(table):
        st.session_state.corner_highlight=table.Corner.iloc[rows[0]];st.session_state.last_corner_rows=rows
    if st.session_state.get('corner_highlight') not in choices:st.session_state.corner_highlight='Full lap'
    selected=st.selectbox('Highlight corner in map and traces',choices,key='corner_highlight')
    marker=None if selected=='Full lap' else float(table[table.Corner==selected]['Distance (m)'].iloc[0])
    traces,corners,maptab,stint=st.tabs(['Traces','Corners','Track map','Pace & stints'])
    def theme(fig):
        fig.update_layout(template='plotly_dark',paper_bgcolor='#08090a',plot_bgcolor='#111416',font=dict(family='Arial',color='#d9dde3'),margin=dict(l=45,r=15,t=35,b=45));return fig
    with traces:
        fig=make_subplots(rows=5,cols=1,shared_xaxes=True,vertical_spacing=.035)
        for row,(channel,unit) in enumerate([('Speed','km/h'),('Throttle','%'),('Brake','on/off %'),('Gear',''),('Delta','s')],1):
            for n,color in ((1,'#00d8ec'),(2,'#ef5560')) if channel!='Delta' else ((0,'#f7f8f8'),):
                fig.add_trace(go.Scatter(x=a.Distance,y=a[f'{channel}{n}' if n else channel],name=names[n-1] if n else 'Time delta',legendgroup=str(n),showlegend=row==1 or n==0,line=dict(color=color)),row=row,col=1)
            fig.update_yaxes(title_text=f'{channel} {unit}',row=row,col=1)
            if marker is not None:fig.add_vrect(x0=marker-180,x1=marker+180,fillcolor='#e10600',opacity=.1,line_width=0,row=row,col=1)
        fig.update_xaxes(title_text='Distance (m)',row=5,col=1);fig.update_layout(height=950);st.plotly_chart(theme(fig),width='stretch')
        st.dataframe(pd.DataFrame([{f'Sector {n} delta (s)':seconds_delta(laps[0].get(f'Sector{n}Time'),laps[1].get(f'Sector{n}Time')) for n in (1,2,3)}]),hide_index=True,width='stretch')
        with st.expander('Telemetry data & export'):
            st.dataframe(a.iloc[::10],hide_index=True,width='stretch');st.download_button('Download aligned CSV',a.to_csv(index=False),'aligned-laps.csv')
    with corners:
        st.caption('1 = primary; 2 = comparison. Positive braking delta means primary brakes later. Approximate markers; missing measurements remain unavailable.')
        if table.empty:st.info('Circuit metadata unavailable.')
        else:
            st.dataframe(table,hide_index=True,width='stretch',on_select='rerun',selection_mode='single-row',key='cornertable')
            with st.expander('Corner comparison table'):st.table(table)
    with maptab:
        if {'X1','Y1'}.issubset(a.columns):
            fig=go.Figure(go.Scatter(x=a.X1,y=a.Y1,mode='markers',marker=dict(size=4,color=a.Speed1,colorscale='Viridis',colorbar=dict(title='km/h')),name=names[0]))
            if marker is not None:
                focus=a[(a.Distance>=marker-180)&(a.Distance<=marker+180)];fig.add_trace(go.Scatter(x=focus.X1,y=focus.Y1,mode='lines',line=dict(color='#ff595e',width=8),name=selected))
            fig.update_yaxes(scaleanchor='x',scaleratio=1,title='Y (FastF1 position units)');fig.update_xaxes(title='X (FastF1 position units)');st.plotly_chart(theme(fig),width='stretch')
        else:st.info('Position data unavailable.')
    with stint:
        pace=result['pace'].dropna(subset=['Lap seconds','Session minutes']).copy()
        compounds=st.multiselect('Compound filter',sorted(pace.Compound.dropna().unique()),default=sorted(pace.Compound.dropna().unique()))
        stints=st.multiselect('Stint filter',sorted(pace.Stint.dropna().unique()),default=sorted(pace.Stint.dropna().unique()))
        rain=st.selectbox('Weather filter',['All','Dry','Wet']);pace=pace[pace.Compound.isin(compounds)&pace.Stint.isin(stints)]
        if rain!='All':pace=pace[pace.Rainfall==(rain=='Wet')]
        st.subheader('Session pace evolution');st.caption('Fuel, traffic, weather and tyre choice affect lap time. This is not a physical rubbering-in index.')
        fig=go.Figure()
        for driver,points in pace.groupby('Driver'):fig.add_trace(go.Scatter(x=points['Session minutes'],y=points['Lap seconds'],mode='markers',name=driver,text=points.Compound))
        fig.update_xaxes(title='Elapsed session (minutes)');fig.update_yaxes(title='Lap time (seconds)');st.plotly_chart(theme(fig),width='stretch')
        st.dataframe(pace[['Driver','LapNumber','Session minutes','Lap seconds','Compound','Stint','Rainfall']],hide_index=True,width='stretch')
        estimates=degradation(pace) if result['kind']=='R' else []
        st.subheader('Comparable dry race stints');st.caption('At least five accurate green-flag non-pit laps of one compound per driver/stint. Observed pace slope with approximate regression uncertainty; no fuel/traffic correction. Tyre-only degradation cannot be isolated.')
        if estimates:st.dataframe(pd.DataFrame(estimates),hide_index=True,width='stretch')
        else:st.info('Degradation unavailable: need at least five comparable dry race laps per stint.')
