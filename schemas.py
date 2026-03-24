from typing import Any, Dict

from hospital_data import VEHICLE_CAPACITY

CONFIG_SCHEMA_EXAMPLE: Dict[str, Any] = {
    "population_size": 100,
    "n_generations": 80,
    "mutation_prob": 0.3,
    "top_for_selection": 10,
    "vehicle_capacity": 15,
    "n_vehicles": 2,
    "weights": {"distance": 0.3, "priority": 0.5, "capacity": 0.2},
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "population_size": 100,
    "n_generations": 50,
    "mutation_prob": 0.5,
    "top_for_selection": 10,
    "vehicle_capacity": VEHICLE_CAPACITY,
    "n_vehicles": 2,
    "weights": {"distance": 0.3, "priority": 0.5, "capacity": 0.2},
}

