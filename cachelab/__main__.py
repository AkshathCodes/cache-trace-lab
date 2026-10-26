"""Run with python -m cachelab TRACE --size BYTES --line-size BYTES --ways N."""

import argparse
import json
from pathlib import Path

from .cache import Cache, CacheConfig, parse_trace


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a read-only set-associative cache.")
    parser.add_argument("trace", type=Path, help="one decimal or 0x hex address per line")
    parser.add_argument("--size", type=int, default=1024, help="cache capacity in bytes (default: 1024)")
    parser.add_argument("--line-size", type=int, default=16, help="line size in bytes (default: 16)")
    parser.add_argument("--ways", type=int, default=1, help="associativity (default: 1)")
    parser.add_argument("--policy", choices=("lru", "fifo"), default="lru")
    args = parser.parse_args()
    try:
        cache = Cache(CacheConfig(args.size, args.line_size, args.ways, args.policy))
        with args.trace.open(encoding="utf-8") as source:
            for address in parse_trace(source):
                cache.access(address)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(cache.report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
