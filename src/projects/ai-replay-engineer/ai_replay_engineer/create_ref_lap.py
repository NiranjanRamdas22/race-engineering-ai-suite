import pandas as pd
import numpy as np

# Generate high-fidelity benchmark Silverstone lap (5,891 meters, lap time approx 87.5s)
distances = np.linspace(0, 5891, 600)
data = []

# Corner locations at Silverstone
# T1 (Abbey): ~700m
# T3 (Village): ~1300m
# T4 (The Loop): ~1550m
# T6 (Brooklands): ~2400m
# T7 (Luffield): ~2700m
# T9 (Copse): ~3600m
# T10-12 (Maggotts/Becketts): ~3950m - 4300m
# T15 (Stowe): ~4950m
# T16 (Vale): ~5500m
# T17 (Club): ~5700m

time_elapsed = 0.0

for d in distances:
    # Baseline speed profile
    if d < 650:
        # Pit straight into Abbey
        speed = 295 - (d / 650) * 45
        throttle = 1.0 if d < 550 else 0.4
        brake = 0.0 if d < 600 else 0.6
        gear = 7
    elif d < 1200:
        # Abbey to Village
        speed = 190 + np.sin(d / 100) * 30
        throttle = 0.8
        brake = 0.0
        gear = 5
    elif d < 1600:
        # The Loop (tight hairpin)
        speed = 88 + np.sin(d / 80) * 12
        throttle = 0.35 if d > 1450 else 0.0
        brake = 0.85 if d < 1450 else 0.0
        gear = 2
    elif d < 2350:
        # Wellington Straight
        speed = 120 + ((d - 1600) / 750) * 175
        throttle = 1.0
        brake = 0.0
        gear = min(8, 3 + int((d - 1600) / 150))
    elif d < 2800:
        # Brooklands & Luffield
        speed = 115 + np.cos(d / 120) * 25
        throttle = 0.5
        brake = 0.7 if (2350 < d < 2450 or 2650 < d < 2750) else 0.0
        gear = 3
    elif d < 3550:
        # National Straight into Copse
        speed = 150 + ((d - 2800) / 750) * 155
        throttle = 1.0
        brake = 0.0
        gear = 7
    elif d < 4350:
        # Copse, Maggotts & Becketts (High speed esses)
        speed = 240 + np.sin(d / 150) * 45
        throttle = 0.75
        brake = 0.3 if 4100 < d < 4200 else 0.0
        gear = 6
    elif d < 4900:
        # Hanger Straight
        speed = 210 + ((d - 4350) / 550) * 115
        throttle = 1.0
        brake = 0.0
        gear = 8
    elif d < 5400:
        # Stowe corner
        speed = 180 + np.sin(d / 100) * 20
        throttle = 0.6
        brake = 0.75 if 4900 < d < 5000 else 0.0
        gear = 5
    else:
        # Vale chicane and Club
        speed = 110 + np.sin(d / 90) * 35
        throttle = 0.6 if d > 5650 else 0.0
        brake = 0.9 if 5420 < d < 5520 else 0.0
        gear = 3

    # Add small step time
    dist_step = 5891 / 600
    speed_ms = max(speed * (1000 / 3600), 10.0)
    time_elapsed += dist_step / speed_ms

    data.append({
        "distance": round(d, 1),
        "timestamp": round(time_elapsed, 3),
        "speed": round(speed, 1),
        "throttle": round(throttle, 2),
        "brake": round(brake, 2),
        "gear": int(gear)
    })

df = pd.DataFrame(data)
df.to_csv("c:/Users/niran/Desktop/PORTFOLIO builds/projects/ai-replay-engineer/ai_replay_engineer/reference_lap.csv", index=False)
print("reference_lap.csv created successfully with", len(df), "telemetry points.")
