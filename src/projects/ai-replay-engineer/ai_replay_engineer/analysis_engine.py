import pandas as pd
import numpy as np
import os
from typing import List, Dict, Optional, Any

CORNERS = [
    (0, 800, "Turn 1-2 (Abbey / Farm)"),
    (800, 1400, "Turn 3 (Village)"),
    (1400, 1750, "Turn 4 (The Loop)"),
    (1750, 2400, "Wellington Straight"),
    (2400, 2600, "Turn 6 (Brooklands)"),
    (2600, 2900, "Turn 7 (Luffield)"),
    (2900, 3500, "Woodcote / National Straight"),
    (3500, 3850, "Turn 9 (Copse Corner)"),
    (3850, 4400, "Turns 10-14 (Maggotts & Becketts)"),
    (4400, 4900, "Hanger Straight"),
    (4900, 5350, "Turn 15 (Stowe Corner)"),
    (5350, 5650, "Turn 16 (Vale Chicane)"),
    (5650, 5891, "Turn 17 (Club Corner)")
]

class TelemetryAnalyzer:
    def __init__(self, reference_lap_path: Optional[str] = None):
        self.ref_lap = None
        if reference_lap_path is None:
            default_path = os.path.join(os.path.dirname(__file__), "reference_lap.csv")
            if os.path.exists(default_path):
                self.load_reference_lap(default_path)
        else:
            self.load_reference_lap(reference_lap_path)

    def load_reference_lap(self, path: str):
        self.ref_lap = pd.read_csv(path)

    def get_corner_name(self, distance: float) -> str:
        for start, end, name in CORNERS:
            if start <= distance <= end:
                return name
        return "Sector Transition"

    def analyze_sample(self, current_sample: Dict[str, Any], distance: float) -> List[Dict[str, Any]]:
        """
        Deterministic high-frequency comparison against benchmark telemetry.
        Returns actionable engineering alerts with corner context and delta.
        """
        if self.ref_lap is None:
            return []

        # Find closest point in reference lap
        idx = (self.ref_lap['distance'] - distance).abs().idxmin()
        ref_point = self.ref_lap.iloc[idx]
        corner = self.get_corner_name(distance)

        alerts = []
        speed_delta = round(current_sample['speed'] - ref_point['speed'], 1)

        # 1. Braking point analysis
        curr_brake = current_sample.get('brake', 0.0)
        ref_brake = ref_point.get('brake', 0.0)

        if curr_brake > 0.3 and ref_brake < 0.1:
            alerts.append({
                "type": "BRAKING_EARLY",
                "severity": "MEDIUM",
                "corner": corner,
                "msg": f"Braking too early into {corner}. Lost entry momentum ({speed_delta:+} km/h delta)."
            })
        elif curr_brake < 0.1 and ref_brake > 0.4:
            alerts.append({
                "type": "BRAKING_LATE",
                "severity": "HIGH",
                "corner": corner,
                "msg": f"Overshooting braking point in {corner}! High risk of lockup or running wide."
            })

        # 2. Throttle application on corner exit
        curr_throttle = current_sample.get('throttle', 0.0)
        ref_throttle = ref_point.get('throttle', 0.0)

        if curr_throttle < ref_throttle - 0.25 and ref_throttle > 0.5:
            alerts.append({
                "type": "THROTTLE_HESITATION",
                "severity": "LOW",
                "corner": corner,
                "msg": f"Hesitant throttle pick-up leaving {corner}. Reference is already at {int(ref_throttle*100)}% throttle."
            })

        # 3. Apex / Mid-corner speed deficit
        if speed_delta < -12.0:
            alerts.append({
                "type": "SPEED_DEFICIT",
                "severity": "MEDIUM",
                "corner": corner,
                "msg": f"Significant speed deficit ({speed_delta} km/h) through {corner}. Tighten line."
            })

        return alerts
