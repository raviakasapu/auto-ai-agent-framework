from __future__ import annotations

import argparse
from pathlib import Path

from agent_framework.utils.config_loader import load_agent_from_yaml
from agent_framework.utils.manifest_generator import save_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an Agent Manifest JSON file from YAML config.")
    parser.add_argument("--config", required=True, help="Path to agent YAML config")
    parser.add_argument("--output", required=True, help="Output path for manifest JSON")
    args = parser.parse_args()

    config_path = Path(args.config)
    output_path = Path(args.output)

    agent = load_agent_from_yaml(str(config_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_manifest(agent, str(output_path))
    print(f"Manifest saved to {output_path}")


if __name__ == "__main__":
    main()

