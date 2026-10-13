import time
from sim_emulator import SimEmulator
from analysis_engine import AnalysisEngine
from race_engineer_ai import RaceEngineerAI

def main():
    print("Starting AI Race Engineer System...")
    print("Connecting to sim telemetry... [MOCK MODE]")
    print("-" * 50)

    sim = SimEmulator()
    engine = AnalysisEngine()
    ai = RaceEngineerAI()

    prev_frame = None
    
    try:
        # Run for a few full laps
        for frame_count in range(200):
            frame = sim.get_telemetry_frame()
            
            # 1. Analyze the telemetry
            events = engine.analyze_frame(frame, prev_frame)
            
            # 2. Generate AI feedback if events occurred
            radio_msg = ai.generate_radio_message(events, frame)
            
            # 3. Display telemetry (simplified) and Radio messages
            if radio_msg:
                print(f"\n[RADIO]: {radio_msg}")
            
            # Periodically print status to show the sim is running
            if frame_count % 20 == 0:
                print(f"Lap Progress: {frame['corner']} | Speed: {frame['speed']}km/h | Tire FL: {frame['tire_temps']['FL']:.1f}C")

            prev_frame = frame
            time.sleep(0.1) # Simulate real-time flow
            
    except KeyboardInterrupt:
        print("\nSystem shutdown.")

if __name__ == "__main__":
    main()
