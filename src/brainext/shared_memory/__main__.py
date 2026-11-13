"""One bounded JSON request on stdin; no secrets or raw exceptions on stderr."""

import argparse
import json
import sys
from pathlib import Path

from brainext.shared_memory.service import MemoryService, response


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("request_too_large")
        request = json.loads(raw.decode("utf-8-sig"))
        result = MemoryService(args.vault, args.registry).handle(request)
    except (ValueError, TypeError, KeyError):
        result = response("invalid", warnings=["invalid_request"])
    except Exception:
        result = response("unavailable", warnings=["memory_unavailable"])
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
