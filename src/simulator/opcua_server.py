from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any

try:
    from .contracts import OPCUA_TAGS
    from .motor_model import MotorSimulator
except ImportError:  # pragma: no cover - allows direct script execution.
    from contracts import OPCUA_TAGS
    from motor_model import MotorSimulator


def load_config(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without dependency.
        raise SystemExit("PyYAML is required. Install dependencies with: python -m pip install -e .") from exc

    with path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def config_value(
    config: dict[str, Any],
    section: str,
    key: str,
    default: Any,
    env_name: str | None = None,
) -> Any:
    if env_name and env_name in os.environ:
        return os.environ[env_name]
    return config.get(section, {}).get(key, default)


def build_server(endpoint: str, namespace_uri: str, display_name: str) -> tuple[Any, int, dict[str, Any]]:
    try:
        from opcua import Server
    except ImportError as exc:  # pragma: no cover - exercised only without dependency.
        raise SystemExit("opcua is required. Install dependencies with: python -m pip install -e .") from exc

    server = Server()
    server.set_endpoint(endpoint)
    server.set_server_name("Condition Monitoring Lab OPC UA Server")

    namespace_index = server.register_namespace(namespace_uri)
    objects = server.get_objects_node()
    lab = objects.add_object(namespace_index, "Lab")
    motor = lab.add_object(namespace_index, display_name)

    nodes: dict[str, Any] = {}
    for tag in OPCUA_TAGS:
        initial_value: str | float = "" if tag in {"severity", "failure_mode"} else 0.0
        node = motor.add_variable(namespace_index, tag, initial_value)
        node.set_writable(False)
        nodes[tag] = node

    return server, namespace_index, nodes


def run(config_path: Path) -> None:
    config = load_config(config_path)

    endpoint = str(config_value(config, "opcua", "endpoint", "opc.tcp://0.0.0.0:4840/lab/opcua/", "OPCUA_ENDPOINT"))
    namespace_uri = str(config_value(config, "opcua", "namespace_uri", "urn:condition-monitoring-lab:mvp"))
    display_name = str(config_value(config, "asset", "display_name", "Motor_001"))
    sample_interval = float(
        config_value(config, "simulation", "sample_interval_seconds", 1.0, "SIM_SAMPLE_INTERVAL_SECONDS")
    )
    scenario_duration = float(
        config_value(config, "simulation", "scenario_duration_seconds", 90.0, "SIM_SCENARIO_DURATION_SECONDS")
    )
    random_seed = int(config_value(config, "simulation", "random_seed", 42, "SIM_RANDOM_SEED"))

    simulator = MotorSimulator(
        tenant_id=str(config_value(config, "asset", "tenant_id", "cliente_demo")),
        plant_id=str(config_value(config, "asset", "plant_id", "lab_virtual")),
        asset_id=str(config_value(config, "asset", "asset_id", "motor_001")),
        source=str(config_value(config, "simulation", "source", "opcua_lab_simulator")),
        scenario_duration_seconds=scenario_duration,
        random_seed=random_seed,
    )

    server, _, nodes = build_server(endpoint, namespace_uri, display_name)
    started_at = time.monotonic()

    logging.info("Starting OPC UA server at %s", endpoint)
    logging.info("Browse path: Objects > Lab > %s", display_name)

    server.start()
    try:
        while True:
            elapsed = time.monotonic() - started_at
            sample = simulator.sample(elapsed)
            values = sample.opcua_values()

            for tag, value in values.items():
                nodes[tag].set_value(value)

            logging.info(
                "%s | rpm=%.1f vib=%.2fmm/s temp=%.2fC us=%.2fdB health=%.1f severity=%s",
                sample.failure_mode.value,
                sample.rpm,
                sample.vibration_rms_mm_s,
                sample.temperature_c,
                sample.ultrasound_db,
                sample.health_score,
                sample.severity.value,
            )
            time.sleep(sample_interval)
    except KeyboardInterrupt:
        logging.info("Stopping OPC UA server")
    finally:
        server.stop()


def parse_args() -> argparse.Namespace:
    default_config = Path(__file__).with_name("config.yaml")
    parser = argparse.ArgumentParser(description="Run the Motor_001 OPC UA simulator.")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help=f"Path to simulator YAML config. Default: {default_config}",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SIM_LOG_LEVEL", "INFO"),
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Console log level.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    run(args.config)


if __name__ == "__main__":
    main()
