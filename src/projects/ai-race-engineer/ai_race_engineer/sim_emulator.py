import random
import time
from typing import Dict, Any

class SimEmulator:
    """
    Illustrative Monza simulator; not a calibrated vehicle or tyre model.
    """
    def __init__(self, seed=42, scenario='Balanced'):
        self.random = random.Random(seed)
        self.scenario = scenario
        self.elapsed = 0.0
        self.frame = 0
        self.lap_length = 200  # Frames per lap

        # Track profile: (start_frame, end_frame, sector_name, min_speed, max_speed, baseline_gear)
        self.track_profile = [
            (0, 45, "Main Straight (Rettifilo)", 310, 350, 8),
            (45, 65, "Turn 1-2 (Variante del Rettifilo)", 75, 110, 2),
            (65, 95, "Curva Grande (Curva Biassono)", 280, 315, 7),
            (95, 115, "Turn 4-5 (Variante della Roggia)", 110, 140, 3),
            (115, 135, "Turns 6-7 (Curva di Lesmo 1 & 2)", 165, 205, 4),
            (135, 160, "Curva del Serraglio & Straight", 295, 335, 8),
            (160, 180, "Turns 8-10 (Variante Ascari)", 170, 220, 5),
            (180, 200, "Turn 11 (Curva Parabolica / Alboreto)", 190, 265, 6),
        ]

        # Dynamic state
        self.current_speed = 320.0
        self.tire_temps = {"FL": 92.0, "FR": 92.0, "RL": 88.0, "RR": 88.0}
        self.tire_wear = {"FL": 100.0, "FR": 100.0, "RL": 100.0, "RR": 100.0}

    def get_telemetry_frame(self) -> Dict[str, Any]:
        self.frame += 1
        self.elapsed += 0.1
        if self.frame > self.lap_length:
            self.frame = 1

        # Current track sector
        segment = self.track_profile[0]
        for s in self.track_profile:
            if s[0] <= self.frame < s[1]:
                segment = s
                break

        start, end, corner_name, min_spd, max_spd, target_gear = segment
        progress = (self.frame - start) / max(1, (end - start))

        # Physics speed curve
        if "Straight" in corner_name or "Grande" in corner_name:
            target_speed = min_spd + progress * (max_spd - min_spd)
            throttle = 100
            brake = 0
            gear = target_gear
        elif "Variante" in corner_name:
            # Heavy braking into chicane, then acceleration out
            if progress < 0.5:
                target_speed = max_spd - (progress * 2) * (max_spd - min_spd)
                brake = int(85 + self.random.uniform(0, 15))
                throttle = 0
                gear = max(1, target_gear - 1)
            else:
                target_speed = min_spd + ((progress - 0.5) * 2) * (max_spd - min_spd)
                brake = 0
                throttle = int(50 + progress * 50)
                gear = target_gear
        else:
            # Sweeping corners (Lesmo, Parabolica)
            target_speed = min_spd + progress * (max_spd - min_spd)
            throttle = 75
            brake = 0
            gear = target_gear

        # Smooth interpolation
        self.current_speed += (target_speed - self.current_speed) * 0.25
        
        # Tire thermodynamics
        target_temp = 112.0 if brake > 40 else (90.0 if throttle == 100 else 99.0)
        for t in self.tire_temps:
            # Front left bears high lateral load at Curva Grande & Parabolica
            lateral_gain = 4.0 if (t == "FL" and ("Grande" in corner_name or "Parabolica" in corner_name)) else 0.0
            self.tire_temps[t] += (target_temp + lateral_gain - self.tire_temps[t]) * 0.035 + self.random.uniform(-0.03, 0.03)
            # Wear
            self.tire_wear[t] = max(0.0, min(100.0, self.tire_wear[t] - 0.0015))

        # Random incident injection
        lap_delta = round(self.random.uniform(-0.05, 0.05), 3)
        if brake > 80 and self.random.random() < (0.12 if self.scenario=='Lockup practice' else 0.04):
            # Lockup event
            brake = 100
            self.current_speed -= 35
            lap_delta = 0.45
            self.tire_temps["FL"] += 6.5

        rpm = int(8000 + (self.current_speed / 350.0) * 4500 + self.random.randint(-150, 150))

        return {
            "frame": self.frame,
            "timestamp": round(self.elapsed,3),
            "distance": self.frame / self.lap_length * 5793,
            "mode": "illustrative simulation",
            "speed": round(max(30.0, self.current_speed), 1),
            "rpm": max(4000, min(13000, rpm)),
            "gear": gear,
            "brake": brake,
            "throttle": throttle,
            "tire_temps": {k: round(v, 1) for k, v in self.tire_temps.items()},
            "tire_wear": {k: round(v, 1) for k, v in self.tire_wear.items()},
            "lap_delta": lap_delta,
            "corner": corner_name
        }

if __name__ == "__main__":
    sim = SimEmulator()
    for _ in range(10):
        print(sim.get_telemetry_frame())
        time.sleep(0.05)
