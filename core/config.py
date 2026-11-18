"""Frozen game constants and configuration parameters.

All constants are centralized here to guarantee that every module
refers to the identical single source of truth without hard-coded magic values.
"""

from typing import Dict

# Preset weights for the scalar edge cost function
# cost(e) = w_d * (D/D_ref) + w_t * (T/T_ref) + w_f * (F/F_ref) + w_r * (R/R_ref) + w_o * (O/O_ref)
# All weights must be non-negative and sum to 1.0.
COST_PRESETS: Dict[str, Dict[str, float]] = {
    "Balanced": {"D": 0.25, "T": 0.25, "F": 0.20, "R": 0.15, "O": 0.15},
    "Speed":    {"D": 0.20, "T": 0.50, "F": 0.10, "R": 0.10, "O": 0.10},
    "Economy":  {"D": 0.20, "T": 0.15, "F": 0.50, "R": 0.10, "O": 0.05},
    "Safety":   {"D": 0.10, "T": 0.15, "F": 0.15, "R": 0.30, "O": 0.30},
}

# Fuel constants
MAX_FUEL: float = 100.0
FUEL_DIFFICULTY_COEFF: float = 0.1  # fuelCost * (1.0 + 0.1 * (difficulty - 1))
NITRO_FUEL_MULTIPLIER: float = 2.0  # 2x fuel rate during nitro boost
MAX_STATION_PURCHASE: float = 40.0   # Max purchase per pit stop
STATION_FIXED_STOP_TIME: float = 3.0 # Extra seconds added to pit stop if purchase > 0
OPPONENT_REFUEL_THRESHOLD: float = 25.0 # Refuel when fuel <= 25% of max capacity

# Nitro constants
MAX_NITRO_CHARGES: int = 3
NITRO_SPEED_MULTIPLIER: float = 1.5
NITRO_DURATION: float = 4.0          # Seconds per charge

# Racing constants
CHAMPIONSHIP_LAPS: int = 3
QUICK_RACE_LAPS: int = 2
DT: float = 0.1                      # Fixed timestep in seconds
MAX_SIM_TIME: float = 600.0          # Maximum race simulation time in seconds
RECOVERY_TIMEOUT: float = 60.0       # Seconds waiting before racer is declared DNF

# Championship points table (1st through 10th)
POINTS_TABLE: list[int] = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
BONUS_POINTS: int = 0

# Event priorities (1 = highest) and standard durations in seconds
PRIORITY_BLOCKAGE: int = 1
PRIORITY_SHORTCUT_TOGGLE: int = 2
PRIORITY_OIL_SPILL: int = 3
PRIORITY_SPEED_RESTRICTION: int = 4
PRIORITY_FUEL_STATION: int = 5
PRIORITY_NITRO_BOOSTER: int = 6

DURATION_OIL_SPILL: float = 20.0
DURATION_SPEED_RESTRICTION: float = 15.0
DURATION_FUEL_STATION: float = 30.0
DURATION_NITRO_BOOSTER: float = 25.0

OIL_SPILL_DIFFICULTY_PENALTY: int = 2
OIL_SPILL_SPEED_CAP: float = 12.0
DEFAULT_SPEED_RESTRICTION_CAP: float = 15.0

# Procedural generation & validation constants
MAX_RETRIES: int = 50
MIN_STATION_SPACING: int = 3
MIN_OBSTACLE_SPACING: int = 2
MAX_DEGREE: int = 4
MAX_ALTERNATIVE_ROUTES: int = 5
MAX_ROUTE_LEN: int = 30
MIN_CHECKPOINTS: int = 10
MIN_SHORTCUTS: int = 2
MIN_FUEL_STATIONS: int = 2
MIN_NITRO_PICKUPS: int = 2
