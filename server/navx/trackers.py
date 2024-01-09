class OffsetTracker:
    def __init__(self, history_length: int):
        self._history = [0.0] * history_length
        self._next_value_history_index = 0
        self._value_offset = 0
    
    def update_history(self, current: float):
        if (self._next_value_history_index >= len(self._history)):
            self._next_value_history_index = 0
        self._history[self._next_value_history_index] = current
        self._next_value_history_index += 1
    
    def get_average(self) -> float:
        return sum(self._history[:]) / len(self._history)
    
    def set_offset(self):
        self._value_offset = self.get_average()
    
    def get_offset(self) -> float:
        return self._value_offset

    def apply_offset(self, value: float) -> float:
        offseted_value = float(value) - self._value_offset
        if (offseted_value < -180):
            offseted_value += 360
        if (offseted_value > 180):
            offseted_value -= 360
        return offseted_value

class InertialDataIntegrator:
    def __init__(self):
        self.reset_displacement()
    
    def reset_displacement(self):
        self.last_velocity = [0.0] * 2
        self.displacement = [0.0] * 2
    
    def update_displacement(self, accel_x_g: float, accel_y_g: float, update_rate_hz: int, is_moving: bool):
        if is_moving:
            accel_m_s2 = [0.0, 0.0]
            curr_velocity_m_s = [0.0, 0.0]
            sample_time = (1.0 / update_rate_hz)
            accel_g = [accel_x_g, accel_y_g]
            for i in range(2):
                accel_m_s2[i] = accel_g[i] * 9.80665
                curr_velocity_m_s[i] = self.last_velocity[i] + (accel_m_s2[i] * sample_time)
                self.displacement[i] += self.last_velocity[i] + (0.5 * accel_m_s2[i] * sample_time * sample_time)
                self.last_velocity[i] = curr_velocity_m_s[i]
        else:
            self.last_velocity = [0.0, 0.0]

    @property
    def velocity_x(self):
        return self.last_velocity[0]
    
    @property
    def velocity_y(self):
        return self.last_velocity[1]
    
    @property
    def velocity_z(self):
        return 0
    
    @property
    def displacement_x(self):
        return self.displacement[0]
    
    @property
    def displacement_y(self):
        return self.displacement[1]
    
    @property
    def displacement_z(self):
        return 0

class ContinuousAngleTracker:
    def __init__(self):
        self.last_angle = 0.0
        self.zero_crossing_count = 0
        self.last_rate = 0.0
        self.first_sample = False
    
    def next_angle(self, new_angle: float):
        # If the first received sample is negative,
        # ensure that the zero crossing count is
        # decremented.
        if self.first_sample:
            self.first_sample = False
            if new_angle < 0:
                self.zero_crossing_count -= 1

        # Calculate delta angle, adjusting appropriately
        # if the current sample crossed the -180/180
        # point.

        bottom_crossing = False
        delta_angle = new_angle - self.last_angle
        # Adjust for wraparound at -180/+180 point
        if delta_angle >= 180.0:
            delta_angle = 360.0 - delta_angle
            bottom_crossing = True
        elif delta_angle <= -180.0:
            delta_angle = 360.0 + delta_angle
            bottom_crossing = True
        self.last_rate = delta_angle

        # If a zero crossing occurred, increment/decrement
        # the zero crossing count appropriately.
        if not bottom_crossing:
            if delta_angle < 0:
                if (new_angle < 0) and (self.last_angle >= 0):
                    self.zero_crossing_count -= 1
            elif delta_angle > 0:
                if (new_angle >= 0) and (self.last_angle < 0):
                    self.zero_crossing_count += 1
        self.last_angle = new_angle

    @property
    def angle(self) -> float:
        accumulated_angle = float(self.zero_crossing_count * 360.0)
        curr_angle = float(self.last_angle)
        if curr_angle < 0:
            curr_angle += 360.0
        accumulated_angle += curr_angle
        return accumulated_angle

    @property
    def rate(self) -> float:
        return self.last_rate