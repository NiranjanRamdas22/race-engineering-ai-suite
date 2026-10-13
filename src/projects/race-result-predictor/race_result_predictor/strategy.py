"""Strategy scenarios are hypothetical elapsed times, separate from ML probabilities."""
import math

def scenario_time(laps,base_pace,pit_laps,pit_loss,degradation):
    if not isinstance(laps,int) or not 1<=laps<=200:raise ValueError('Laps must be 1–200.')
    if not math.isfinite(base_pace) or base_pace<=0 or not math.isfinite(pit_loss) or pit_loss<0:raise ValueError('Pace must be positive and pit loss nonnegative.')
    if not 1<=len(pit_laps)<=2 or sorted(set(pit_laps))!=pit_laps or any(not isinstance(x,int) or not 0<x<laps for x in pit_laps):raise ValueError('Choose one or two unique increasing pit laps inside the race.')
    if len(degradation)!=len(pit_laps)+1 or any(not math.isfinite(x) or x<0 for x in degradation):raise ValueError('Provide nonnegative degradation for every stint.')
    boundaries=[0]+pit_laps+[laps];stints=[];running=0
    for i,(start,end) in enumerate(zip(boundaries,boundaries[1:])):
        n=end-start;seconds=n*base_pace+degradation[i]*n*(n-1)/2;running+=seconds;stints.append({'start_lap':start+1,'end_lap':end,'laps':n,'degradation_s_per_lap':degradation[i],'seconds':seconds})
    return {'total_seconds':running+len(pit_laps)*pit_loss,'pit_seconds':len(pit_laps)*pit_loss,'stints':stints}
