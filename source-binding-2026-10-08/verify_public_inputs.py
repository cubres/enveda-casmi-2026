"""Check the pinned public mounted files before loading any model. No network."""
from pathlib import Path
import argparse
import json
import native_mount_bridge_v5 as bridge
import scoped_mount_resolver_v2 as resolver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument("--contract", type=Path,
                        default=Path(__file__).with_name("input-contract.json"))
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    _, receipt = bridge.qualify_mounts(resolver, args.input_root,
        contract["mounted_bindings"], contract["original_pins"], contract["lineage"])
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
