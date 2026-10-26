"""Print the five documented comparisons as CSV. Run from the repository root."""

import csv
from pathlib import Path
import sys

from cachelab import Cache, CacheConfig, parse_trace


def main() -> None:
    examples = Path(__file__).resolve().parents[1] / "examples"
    scenarios = [
        ("conflict-direct", "conflict.trace", CacheConfig(64, 16, 1)),
        ("conflict-2way", "conflict.trace", CacheConfig(64, 16, 2)),
        ("locality-direct", "locality.trace", CacheConfig(64, 16, 1)),
        ("replacement-lru", "replacement.trace", CacheConfig(32, 16, 2, "lru")),
        ("replacement-fifo", "replacement.trace", CacheConfig(32, 16, 2, "fifo")),
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "scenario", "size_bytes", "line_size_bytes", "ways", "policy",
        "accesses", "hits", "misses", "evictions", "hit_rate",
    ], lineterminator="\n")
    writer.writeheader()
    for name, filename, config in scenarios:
        cache = Cache(config)
        with (examples / filename).open(encoding="utf-8") as source:
            for address in parse_trace(source):
                cache.access(address)
        result = cache.report()
        row = {"scenario": name, **result.pop("config"), **result}
        del row["sets"]
        row["hit_rate"] = f"{result['hit_rate']:.6f}"
        writer.writerow(row)


if __name__ == "__main__":
    main()
