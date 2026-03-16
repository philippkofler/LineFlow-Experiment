'''
Module containing different helper-functions
'''

import random
from lineflow_ef.config import config_probabilities
from lineflow_ef.components_dict import components_dict
from typing import Optional, Tuple, Dict


def weighted_choice(options: dict) -> str:
    """Select an option based on weighted probabilities."""
    opts = [opt for opt, _ in options.items()]
    weights = [weight for _, weight in options.items()]
    return random.choices(opts, weights=weights, k=1)[0]


def generate_configuration(config_probabilities: dict) -> dict:
    """Generate a configuration based on given probabilities."""
    config = {}
    for key, probs in config_probabilities.items():
        if key == 'Options':
            options = [opt for opt, p in probs.items() if random.random() < p]
            config["Options"] = options
        else:
            config[key] = weighted_choice(probs)
    return config


def create_specs(config_probs: dict) -> dict:
    """Create part specifications including configuration and processing times."""
    specs = {}
    configuration = generate_configuration(config_probabilities=config_probs)
    specs['config'] = configuration

    return specs


def build_idle_carrier_spec() -> Tuple[str, int, Dict[str, Dict]]:
    """
    Builds an empty carrier with all values=0
    """
    machine_type = "no_name"
    unique = random.randint(10000, 99999)
    idle_config_id = 0
    machine_worksteps: Dict[str, Dict] = {}

    for station_name, station_data in components_dict.items():
        for component_name in station_data.keys():
            workstep_name = f"leer_{unique}_{component_name}"
            machine_worksteps[workstep_name] = {
                station_name: {
                    'extra_processing_time': 0,
                    'error_probability': 0.0,
                    'error_time': 0
                }
            }

    return machine_type, idle_config_id, machine_worksteps
    

def ComponentSampler(spec_origin: Optional[dict] = None, unique: Optional[str] = None) -> Tuple[str, int, Dict]:
    """Creates the configuration for the machines and provides all the components needed.
    In case of 'leer': creates idle carrier
    
    Idle-Carrier has all stations with the parameters set to 0:
    extra_processing_time=0, error_probability=0.0, error_time=0.
    """

    spec = spec_origin if spec_origin is not None else create_specs(config_probabilities)
    config_id = generate_config_id(spec["config"])

    if isinstance(spec, dict):
        if not spec:
            return build_idle_carrier_spec()
        if any("leer" in str(k).lower() for k in spec.keys()):
            return build_idle_carrier_spec()

    if unique is None:
        unique = str(random.randint(10000, 99999))

    if "Type" not in spec["config"]:
        raise KeyError("Configuration missing required key 'Type'.")
    machine_type = spec['config']['Type']

    machine_worksteps: Dict[str, Dict] = {}

    for station_name, station_data in components_dict.items():
        for component_name, component_data in station_data.items():
            name = f"{machine_type}_{unique}_{component_name}"
            machine_worksteps[name] = {
                station_name: {
                    'extra_processing_time': component_data['processing_time'][machine_type],
                    'error_probability': component_data['error_probability'],
                    'error_time': component_data['error_time']
                }
            }

    return machine_type, config_id, machine_worksteps


def generate_config_id(configuration: dict) -> int:
    """
    Generates a config_id using Mixed-Radix for exclusive groups plus a bitmask for flags.
    """

    EXCLUSIVE_GROUPS = {
        "Type": ["Type_1", "Type_2", "Type_3"],
    }

    FLAGS = [
        "Option_1",
        "Option_2",
        "Option_3",
        "Option_4",
        "Option_5",
    ]

    def compute_radix_multipliers(radices: list[int]) -> list[int]:
        """Return multipliers for mixed-radix encoding: [1, r0, r0*r1, ...]."""
        mult = [1]
        for r in radices[:-1]:
            mult.append(mult[-1] * r)
        return mult

    def encode_groups(config: dict) -> tuple[int, int]:
        """
        Encode exclusive groups in mixed-radix.
        Returns:
            (group_code, RADIX_TOTAL)
        """
        for group in EXCLUSIVE_GROUPS.keys():
            if group not in config:
                raise KeyError(f"Missing required group key '{group}' in configuration.")

        indices: list[int] = []
        radices: list[int] = []
        for group, options in EXCLUSIVE_GROUPS.items():
            val = config[group]
            try:
                idx = options.index(val)
            except ValueError:
                raise ValueError(
                    f"Invalid value '{val}' for group '{group}'. "
                    f"Allowed: {options}"
                )
            indices.append(idx)
            radices.append(len(options))

        multipliers = compute_radix_multipliers(radices)
        group_code = sum(i * m for i, m in zip(indices, multipliers))
        radix_total = 1
        for r in radices:
            radix_total *= r

        return int(group_code), int(radix_total)

    def encode_flags(config: dict) -> int:
        """
        Encode boolean/0/1 flags as a bitmask.
        Supports either individual keys (Option_1=True/False) OR a list under 'Options'.
        """
        bits = 0
        opts_list = set(map(str, config.get("Options", [])))

        for i, name in enumerate(FLAGS):
            if bool(config.get(name, False)) or (name in opts_list):
                bits |= (1 << i)
        return bits

    group_code, radix_total = encode_groups(configuration)
    flags_code = encode_flags(configuration)
    config_id = group_code + flags_code * radix_total
    return int(config_id)
