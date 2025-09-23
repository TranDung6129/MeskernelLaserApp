"""
Geotech Utils - Các utility functions cho Geotech Panel
Chứa các hàm chuyển đổi đơn vị, xử lý dữ liệu và các helper functions
"""
from typing import List, Dict, Any, Optional
import numpy as np


class GeotechUtils:
    """Utility class cho Geotech Panel"""
    
    @staticmethod
    def convert_depth_value(depth_m: float, depth_unit: str) -> float:
        """Chuyển đổi độ sâu từ m sang đơn vị hiện tại"""
        if depth_unit == "mm":
            return depth_m * 1000
        elif depth_unit == "cm":
            return depth_m * 100
        return depth_m  # m

    @staticmethod
    def convert_velocity_value(velocity_ms: float, velocity_unit: str) -> float:
        """Chuyển đổi vận tốc từ m/s sang đơn vị hiện tại"""
        if velocity_unit == "mm/s":
            return velocity_ms * 1000
        elif velocity_unit == "cm/s":
            return velocity_ms * 100
        return velocity_ms  # m/s

    @staticmethod
    def convert_depth_array(depths_m: List[float], depth_unit: str) -> List[float]:
        """Chuyển đổi array độ sâu"""
        return [GeotechUtils.convert_depth_value(d, depth_unit) for d in depths_m]

    @staticmethod
    def convert_velocity_array(velocities_ms: List[float], velocity_unit: str) -> List[float]:
        """Chuyển đổi array vận tốc"""
        return [GeotechUtils.convert_velocity_value(v, velocity_unit) for v in velocities_ms]

    @staticmethod
    def separate_data_by_state(depth_series: List[float], velocity_series: List[float], 
                              state_series: List[str], depth_unit: str = "m", 
                              velocity_unit: str = "m/s") -> Dict[str, Dict[str, List[float]]]:
        """Tách dữ liệu theo trạng thái và chuyển đổi đơn vị"""
        vel_drill, dep_drill = [], []
        vel_stop, dep_stop = [], []
        vel_retract, dep_retract = [], []
        
        for i in range(len(depth_series)):
            st = state_series[i] if i < len(state_series) else ""
            stl = st.lower()
            converted_vel = GeotechUtils.convert_velocity_value(velocity_series[i], velocity_unit)
            converted_dep = GeotechUtils.convert_depth_value(depth_series[i], depth_unit)
            
            if stl.startswith('khoan'):
                vel_drill.append(converted_vel)
                dep_drill.append(converted_dep)
            elif 'rút' in stl or 'rut' in stl:
                vel_retract.append(converted_vel)
                dep_retract.append(converted_dep)
            else:
                vel_stop.append(converted_vel)
                dep_stop.append(converted_dep)
        
        return {
            'drill': {'velocity': vel_drill, 'depth': dep_drill},
            'stop': {'velocity': vel_stop, 'depth': dep_stop},
            'retract': {'velocity': vel_retract, 'depth': dep_retract}
        }

    @staticmethod
    def separate_time_data_by_state(time_series: List[float], depth_series: List[float], 
                                   velocity_series: List[float], state_series: List[str],
                                   depth_unit: str = "m", velocity_unit: str = "m/s") -> Dict[str, Dict[str, List[float]]]:
        """Tách dữ liệu thời gian theo trạng thái"""
        if not time_series:
            return {'drill': {'time': [], 'depth': [], 'velocity': []},
                   'stop': {'time': [], 'depth': [], 'velocity': []},
                   'retract': {'time': [], 'depth': [], 'velocity': []}}
        
        t0 = time_series[0]
        times = [t - t0 for t in time_series]
        
        t_drill, d_drill, v_drill = [], [], []
        t_stop, d_stop, v_stop = [], [], []
        t_retract, d_retract, v_retract = [], [], []
        
        for i in range(len(times)):
            st = state_series[i] if i < len(state_series) else ""
            stl = st.lower()
            converted_dep = GeotechUtils.convert_depth_value(depth_series[i], depth_unit)
            converted_vel = GeotechUtils.convert_velocity_value(velocity_series[i], velocity_unit)
            
            if stl.startswith('khoan'):
                t_drill.append(times[i])
                d_drill.append(converted_dep)
                v_drill.append(converted_vel)
            elif 'rút' in stl or 'rut' in stl:
                t_retract.append(times[i])
                d_retract.append(converted_dep)
                v_retract.append(converted_vel)
            else:
                t_stop.append(times[i])
                d_stop.append(converted_dep)
                v_stop.append(converted_vel)
        
        return {
            'drill': {'time': t_drill, 'depth': d_drill, 'velocity': v_drill},
            'stop': {'time': t_stop, 'depth': d_stop, 'velocity': v_stop},
            'retract': {'time': t_retract, 'depth': d_retract, 'velocity': v_retract}
        }

    @staticmethod
    def calculate_histogram_data(velocity_series: List[float], velocity_unit: str = "m/s", 
                                bins: int = 25) -> tuple:
        """Tính toán dữ liệu histogram cho vận tốc"""
        if not velocity_series or len(velocity_series) < 5:
            return None, None, None
        
        arr = np.array(velocity_series)
        converted_arr = GeotechUtils.convert_velocity_array(velocity_series, velocity_unit)
        
        # Tính range phù hợp với vận tốc khoan nhỏ
        v_min, v_max = np.min(converted_arr), np.max(converted_arr)
        if v_max - v_min < 0.001:  # Nếu range quá nhỏ, mở rộng một chút
            v_center = (v_min + v_max) / 2
            v_min = v_center - 0.005
            v_max = v_center + 0.005
        
        # Tạo bins với range phù hợp
        bin_edges = np.linspace(v_min, v_max, bins)
        counts, edges = np.histogram(converted_arr, bins=bin_edges)
        centers = (edges[:-1] + edges[1:]) / 2.0
        width = (edges[1] - edges[0]) * 0.8
        
        return centers, counts, width

    @staticmethod
    def calculate_stats(depth_series: List[float], velocity_series: List[float], 
                       state_series: List[str], depth_unit: str = "m", 
                       velocity_unit: str = "m/s") -> Dict[str, Any]:
        """Tính toán các thống kê cơ bản"""
        if not depth_series or not velocity_series:
            return {
                "current_depth": 0.0,
                "max_depth": 0.0,
                "current_velocity": 0.0,
                "avg_velocity": 0.0,
                "min_velocity": 0.0,
                "max_velocity": 0.0,
                "state": "",
                "total_samples": 0
            }
        
        current_depth = GeotechUtils.convert_depth_value(depth_series[-1], depth_unit)
        max_depth = GeotechUtils.convert_depth_value(max(depth_series), depth_unit)
        current_velocity = GeotechUtils.convert_velocity_value(velocity_series[-1], velocity_unit)
        avg_velocity = GeotechUtils.convert_velocity_value(sum(velocity_series) / len(velocity_series), velocity_unit)
        min_velocity = GeotechUtils.convert_velocity_value(min(velocity_series), velocity_unit)
        max_velocity = GeotechUtils.convert_velocity_value(max(velocity_series), velocity_unit)
        total_samples = len(velocity_series)
        state = state_series[-1] if state_series else ""
        
        return {
            "current_depth": current_depth,
            "max_depth": max_depth,
            "current_velocity": current_velocity,
            "avg_velocity": avg_velocity,
            "min_velocity": min_velocity,
            "max_velocity": max_velocity,
            "state": state,
            "total_samples": total_samples
        }
