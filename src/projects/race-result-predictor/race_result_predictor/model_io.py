from pathlib import Path
import json,joblib
import math

def load_metadata(folder):
    try:
        meta=json.loads((Path(folder)/'model_metadata.json').read_text(encoding='utf-8'))
        if not isinstance(meta,dict) or meta.get('schema_version')!=1 or meta.get('mode')!='historical':return None
        if not isinstance(meta.get('data_cutoff'),str):return None
        for section,metric in [('evaluation_2025','mae'),('evaluation_2025','brier_score'),('qualifying_order_baseline','mae'),('simple_probability_baseline','brier_score')]:
            if not math.isfinite(float(meta[section][metric])):return None
        return meta
    except (OSError,ValueError,TypeError,KeyError):return None

def load_bundle(folder):
    folder=Path(folder)
    try:
        meta=load_metadata(folder)
        if meta is None:return None,'Historical model metadata unavailable or invalid. Run the documented training pipeline; qualifying baseline remains available.'
        bundle={'metadata':meta}
        for name in ('rank_model','top10_model','scaler','calibrator'):bundle[name]=joblib.load(folder/(name+'.pkl'))
        return bundle,None
    except (OSError,ValueError,EOFError,ImportError,KeyError) as exc:return None,'Historical model artifacts unavailable. Run the documented historical training pipeline; qualifying baseline remains available.'
