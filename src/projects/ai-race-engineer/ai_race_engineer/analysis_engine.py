from typing import List, Dict, Any, Optional

class AnalysisEngine:
    """
    Translates raw telemetry numbers into 'Driving Events' for the AI.
    """
    def __init__(self):
        self.tire_temp_threshold = 110.0
        self.lockup_speed_drop = 40  # Threshold for sudden speed drop during braking
        
    def analyze_frame(self, frame: Dict[str, Any], prev_frame: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        events = []
        
        # 1. Tire Temp Analysis
        for tire, temp in frame["tire_temps"].items():
            if temp > self.tire_temp_threshold:
                events.append({
                    "event": "tire_overheat",
                    "detail": f"{tire} tire is overheating at {temp:.1f}C",
                    "urgency": "Medium"
                })

        # 2. Braking/Lockup Analysis
        if prev_frame:
            speed_diff = prev_frame["speed"] - frame["speed"]
            if frame["brake"] > 90 and speed_diff > self.lockup_speed_drop:
                events.append({
                    "event": "wheel_lockup",
                    "detail": f"Heavy lockup detected in {frame['corner']}. Speed dropped by {speed_diff}km/h",
                    "urgency": "High"
                })

        # 3. Lap Delta Analysis
        if frame["lap_delta"] > 0.3:
            events.append({
                "event": "time_loss",
                "detail": f"Losing significant time ({frame['lap_delta']:.2f}s) in {frame['corner']}",
                "urgency": "Low"
            })

        return events
