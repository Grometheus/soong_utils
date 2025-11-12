#!/usr/bin/env python3

import time
import traceback
import sys

from src.event_system import *





def output_to(out_dir: str) -> None:
    with EventManager(max_workers=32) as mng:

        # Demo: second run should still print because dependency resolves


        # Example for later:
        # tags = sorted_manifest_tags()
        # with open(join(out_dir, "manifest_tags.json"), "w", encoding="utf-8") as f:
        #     json.dump(tags, f, indent=2, ensure_ascii=False)
        # for tag in tags:
        #     mng.enqueue_event(AndroidVersionEvent(out_dir, tag))


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: collect_data.py OUTPUT_DIR")
        sys.exit(1)

    output = abspath(sys.argv[1])
    if not exists(output) or not isdir(output):
        print("Error: OUTPUT_DIR must be an existing directory")
        sys.exit(1)

    output_to(output)


if __name__ == "__main__":
    main()
