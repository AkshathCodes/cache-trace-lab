"""Address-trace cache model; no CPU timing or writeback simulation."""

from dataclasses import dataclass
from collections.abc import Iterable, Iterator
import re


@dataclass(frozen=True)
class CacheConfig:
    size: int
    line_size: int
    ways: int
    policy: str = "lru"

    def __post_init__(self):
        for name in ("size", "line_size", "ways"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0 or value & (value - 1):
                raise ValueError(f"{name} must be a positive power-of-two integer")
        if self.line_size * self.ways > self.size:
            raise ValueError("line_size * ways cannot exceed cache size")
        if self.policy not in ("lru", "fifo"):
            raise ValueError("policy must be lru or fifo")

    @property
    def sets(self) -> int:
        return self.size // (self.line_size * self.ways)


class Cache:
    def __init__(self, config: CacheConfig):
        self.config = config
        # Oldest line is at index zero. FIFO hits preserve this order.
        self._sets: list[list[int]] = [[] for _ in range(config.sets)]
        self._accesses = 0
        self._hits = 0
        self._evictions = 0

    def access(self, address: int) -> bool:
        if type(address) is not int or address < 0:
            raise ValueError("address must be a nonnegative integer")
        block = address // self.config.line_size
        bucket = self._sets[block % self.config.sets]
        tag = block // self.config.sets
        self._accesses += 1
        if tag in bucket:
            self._hits += 1
            if self.config.policy == "lru":
                bucket.remove(tag)
                bucket.append(tag)
            return True
        if len(bucket) == self.config.ways:
            bucket.pop(0)
            self._evictions += 1
        bucket.append(tag)
        return False

    def report(self) -> dict:
        return {
            "config": {"size_bytes": self.config.size, "line_size_bytes": self.config.line_size,
                       "ways": self.config.ways, "sets": self.config.sets,
                       "policy": self.config.policy},
            "accesses": self._accesses,
            "hits": self._hits,
            "misses": self._accesses - self._hits,
            "evictions": self._evictions,
            "hit_rate": self._hits / self._accesses if self._accesses else 0.0,
        }


def parse_trace(lines: Iterable[str]) -> Iterator[int]:
    for line_number, line in enumerate(lines, 1):
        value = line.partition("#")[0].strip()
        if not value:
            continue
        if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|[0-9]+)", value):
            raise ValueError(f"line {line_number}: expected decimal or 0x hex address, got {value!r}")
        try:
            yield int(value, 16 if value.lower().startswith("0x") else 10)
        except ValueError as error:
            raise ValueError(f"line {line_number}: address exceeds Python's integer parsing limit") from error
