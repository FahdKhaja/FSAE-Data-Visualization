import pandas as pd
import numpy as np
import math
import datetime
import random

class RealisticRaceGenerator:
    def __init__(self, start_time=None):
        self.current_time = start_time if start_time else datetime.datetime.now()
        self.dt = 0.1  # 10Hz
        
        # Car State
        self.speed_mps = 0
        self.dist_m = 0          
        self.track_position_m = 0 
        self.lap = 1
        self.batt_level = 100.0
        self.batt_temp = 30.0
        self.motor_temp = 40.0
        self.voltage = 400.0
        
        # --- PHYSICS CONSTANTS ---
        self.max_speed = 42.0 
        self.accel_rate = 4.0
        self.brake_rate = 10.0
        self.track_length = 4000 
        
        # Track Generation
        self.track_points = 1000
        x = np.linspace(0, 2*np.pi, self.track_points)
        self.track_lat_base = 45.5017 
        self.track_long_base = -73.5673
        self.shape_x = 1000 * (np.cos(x) + 0.6 * np.cos(2*x) - 0.1 * np.sin(3*x)) 
        self.shape_y = 1200 * (np.sin(x) + 0.1 * np.sin(2*x))
        
        self.target_speeds = self._generate_speed_profile()
        
        # Driver Variability
        self.driver_aggression = 1.0 
        self.racing_line_offset = 0.0 

    def _generate_speed_profile(self):
        speeds = []
        for i in range(self.track_points):
            p_prev = (self.shape_x[i-1], self.shape_y[i-1])
            p_curr = (self.shape_x[i], self.shape_y[i])
            p_next = (self.shape_x[(i+1)%self.track_points], self.shape_y[(i+1)%self.track_points])
            
            v1 = np.array(p_curr) - np.array(p_prev)
            v2 = np.array(p_next) - np.array(p_curr)
            
            det = np.linalg.det([v1, v2])
            dot = np.dot(v1, v2)
            angle = math.atan2(det, dot)
            
            curvature = abs(angle)
            
            corner_speed = 15 + (1.0 - min(curvature * 6, 1.0)) * (self.max_speed - 15)
            speeds.append(corner_speed)
            
        return pd.Series(speeds).rolling(window=60, min_periods=1, center=True).mean().values

    def _update_driver_state(self):
        self.driver_aggression += np.random.normal(0, 0.005)
        self.driver_aggression = np.clip(self.driver_aggression, 0.90, 1.10)
        self.racing_line_offset += np.random.normal(0, 0.05)
        self.racing_line_offset = np.clip(self.racing_line_offset, -4.0, 4.0)

    def generate_batch(self, num_points):
        data = []
        
        for _ in range(num_points):
            self._update_driver_state()
            
            # 1. Determine Track Index
            track_pct = (self.track_position_m % self.track_length) / self.track_length
            idx = int(track_pct * self.track_points)
            idx = min(idx, self.track_points - 1)
            
            # 2. Driver Logic
            perceived_target = self.target_speeds[idx] * self.driver_aggression
            speed_error_margin = np.random.normal(0, 1.5) 
            
            throttle = 0
            brake = 0
            
            if self.speed_mps < (perceived_target + speed_error_margin):
                tremor = np.random.normal(0, 2.0)
                gap = (perceived_target - self.speed_mps)
                base_throttle = min(gap * 5.0, 100.0)
                throttle = np.clip(base_throttle + tremor, 0, 100)
                self.speed_mps += (self.accel_rate * (throttle/100.0)) * self.dt
            else:
                gap = (self.speed_mps - perceived_target)
                base_brake = min(gap * 10.0, 100.0)
                tremor = np.random.normal(0, 3.0)
                brake = np.clip(base_brake + tremor, 0, 100)
                self.speed_mps -= (self.brake_rate * (brake/100.0)) * self.dt
            
            self.speed_mps = max(0, self.speed_mps)
            
            # 3. Physics & Distance
            dist_step_odometer = self.speed_mps * self.dt
            self.dist_m += dist_step_odometer
            
            efficiency = 1.0 - (self.racing_line_offset / 600.0)
            dist_step_track = dist_step_odometer * efficiency
            
            prev_track_pos = self.track_position_m
            self.track_position_m += dist_step_track
            
            if int(self.track_position_m / self.track_length) > int(prev_track_pos / self.track_length):
                self.lap += 1
                self.driver_aggression = np.random.normal(1.0, 0.05)

            # 4. Telemetry Calculation (UPDATED FOR HIGH CONSUMPTION)
            rpm = (self.speed_mps * 150) + np.random.normal(0, 100)
            
            # INCREASED CURRENT DRAW:
            # Changed multiplier from 2.0 to 2.3 and base load from 2.0 to 15.0
            # This simulates a heavier load on the battery
            bat_cur = (throttle * 2.3) + 15.0 + np.random.normal(0, 2)
            bat_cur = max(0.5, bat_cur) 
            
            voltage_sag = bat_cur * 0.04
            self.voltage = 400.0 - (100 - self.batt_level)*0.6 - voltage_sag + np.random.normal(0, 0.2)
            
            # Energy in kWh
            energy_usage = (bat_cur * self.voltage * self.dt) / 3600000 
            
            # INCREASED CONSUMPTION FACTOR:
            # Changed from 4.0 to 6.2
            # This effectively shrinks the battery capacity, making % drop faster
            self.batt_level -= energy_usage * 25
            self.batt_level = max(0, self.batt_level) # Prevent negative battery
            
            # Temp rises faster due to higher current
            self.batt_temp += (abs(bat_cur) * 0.0015 * self.dt) - ((self.batt_temp - 30) * 0.01 * self.dt)
            self.motor_temp += (abs(bat_cur) * 0.006 * self.dt) - ((self.motor_temp - 40) * 0.06 * self.dt)

            # 5. GPS
            lat_perfect_offset = self.shape_y[idx] / 111000
            long_perfect_offset = self.shape_x[idx] / (111000 * math.cos(math.radians(self.track_lat_base)))
            
            dx = self.shape_x[(idx+1)%self.track_points] - self.shape_x[idx-1]
            dy = self.shape_y[(idx+1)%self.track_points] - self.shape_y[idx-1]
            norm_len = math.sqrt(dx*dx + dy*dy)
            if norm_len == 0: norm_len = 1
            
            perp_x = -dy / norm_len
            perp_y = dx / norm_len
            
            final_lat = self.track_lat_base + lat_perfect_offset + (perp_y * self.racing_line_offset / 111000)
            final_long = self.track_long_base + long_perfect_offset + (perp_x * self.racing_line_offset / (111000 * math.cos(math.radians(self.track_lat_base))))

            # 6. Data Row
            row = {
                "ID": 101,
                "TIMESTAMP": self.current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                "BATCUR": round(bat_cur, 2),
                "BATT": round(self.batt_level, 2),
                "BATTMP": round(self.batt_temp, 2),
                "BRAKE": round(brake, 1),
                "DIST": round(self.dist_m, 2),
                "LAPS": self.lap,
                "MOTTMP": round(self.motor_temp, 2),
                "RPM": int(rpm),
                "SPEED": round(self.speed_mps * 3.6, 1), 
                "THRTL": round(throttle, 1),
                "VOLT": round(self.voltage, 1),
                "LAT": round(final_lat, 6),
                "LONG": round(final_long, 6)
            }
            
            data.append(row)
            self.current_time += datetime.timedelta(seconds=self.dt)
            
        return pd.DataFrame(data)

# --- GENERATE ---
if __name__ == "__main__":
    gen = RealisticRaceGenerator()

    # Generate 10,000 points (1000 seconds)
    df = gen.generate_batch(10000) 

    # --- VERIFICATION ---
    start_batt = df.iloc[0]['BATT']
    end_batt = df.iloc[-1]['BATT']
    
    print(f"Start Battery: {start_batt}%")
    print(f"End Battery:   {end_batt}%")
    print(f"Total Drop:    {round(start_batt - end_batt, 2)}%")
    
    # Save
    df.to_csv("race_data_high_drain.csv", index=False)
    print("\nFile saved: race_data_high_drain.csv")