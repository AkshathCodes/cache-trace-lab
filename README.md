# Cache Trace Lab

[![Python tests](https://github.com/AkshathCodes/cache-trace-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/AkshathCodes/cache-trace-lab/actions/workflows/ci.yml)

**A small set-associative cache simulator for exploring address mapping, spatial locality, and LRU versus FIFO replacement.**

Replay hand-checkable address traces and compare cache organizations without installing packages. The model reports hits, misses, evictions, and hit rate. Its results are properties of the chosen model and trace, not measurements of a real CPU.

## Quickstart

Requires Python 3.10+. Everything uses the standard library; there is no package installation step. Run commands from the repository root.

```sh
git clone https://github.com/AkshathCodes/cache-trace-lab.git
cd cache-trace-lab
python -m cachelab examples/conflict.trace --size 64 --line-size 16 --ways 2
python -m experiments.compare
python -m unittest discover -s tests -v
```

The first command produces:

```json
{
  "accesses": 8,
  "config": {
    "line_size_bytes": 16,
    "policy": "lru",
    "sets": 2,
    "size_bytes": 64,
    "ways": 2
  },
  "evictions": 0,
  "hit_rate": 0.75,
  "hits": 6,
  "misses": 2
}
```

## Reproducible experiments

[`examples/results.csv`](examples/results.csv) is reproduced by `python -m experiments.compare`. Tests check both the numeric outcomes and the exact CSV output.

| Scenario | Capacity | Ways | Policy | Hits / accesses | Hit rate |
| --- | --- | --- | --- | --- | --- |
| Alternating conflicting blocks | 64 B | 1 | LRU | 0 / 8 | 0% |
| Same conflicting blocks | 64 B | 2 | LRU | 6 / 8 | 75% |
| Nearby addresses, then reuse | 64 B | 1 | LRU | 14 / 16 | 87.5% |
| Replacement-order trace | 32 B | 2 | LRU | 2 / 5 | 40% |
| Same replacement-order trace | 32 B | 2 | FIFO | 1 / 5 | 20% |

All rows use 16-byte lines. In the conflict trace, addresses `0x00` and `0x40` map to the same direct-mapped set. Two ways allow both blocks to stay resident. In the locality trace, nearby addresses reuse two lines. In the replacement trace `0, 16, 0, 32, 0`, LRU refreshes block 0 on its first hit; FIFO preserves insertion order and later evicts it.

These tiny traces isolate particular effects. They do not establish that a policy or associativity is always better, and they do not quantify processor speedup.

## Model and input contract

- Each reference is one read-address lookup. There are no access sizes, stores, dirty bits, or writebacks.
- Capacity, line size, and ways must be positive powers of two. `line_size * ways` cannot exceed capacity. `ways = 1` is direct-mapped; `ways = size / line_size` is fully associative.
- Each set starts empty. On a miss into a full set, its oldest line is evicted. LRU moves a hit to the newest position; FIFO does not.
- Trace files contain one nonnegative decimal address or `0x`-prefixed hexadecimal address per line. Blank lines and `#` comments are allowed. Leading zeroes remain decimal: `016` means sixteen.
- Invalid geometry, unreadable files, and invalid trace lines exit with status 2. Trace diagnostics include the original line number. No partial JSON report is emitted.
- Addresses use Python integers, with no fixed CPU address width. Extremely long decimal input is subject to Python's configured integer parsing limit.

Mapping:

```text
block = address // line_size
set   = block % number_of_sets
tag   = block // number_of_sets
number_of_sets = size // (line_size * ways)
```

An empty trace reports zero accesses and hit rate `0.0`.

## Python API

```python
from cachelab import Cache, CacheConfig

cache = Cache(CacheConfig(size=64, line_size=16, ways=2, policy="lru"))
for address in [0, 64, 0, 64]:
    print(cache.access(address))  # False, False, True, True
print(cache.report()["hits"])    # 2
```

`Cache.access` rejects negative and non-integer addresses before changing counters. `parse_trace` accepts an iterable of text lines, so analysis code can stream a file rather than loading its entire trace into memory.

## Verification and limits

The suite checks manual mapping/counter examples, line boundaries, capacity evictions, zero and large addresses, LRU/FIFO divergence, malformed input, subprocess CLI behavior, and reproducible examples. A second simulator in the tests uses timestamp-based replacement to cross-check 500 seeded addresses across eight configurations.

CI runs Python 3.10 and 3.12 on Linux and Windows. The model omits cache hierarchies, prefetching, coherence, TLBs, virtual-to-physical translation, latency, bandwidth, and timing. It does not categorize compulsory/conflict/capacity misses. See the [Cachegrind manual's simulation discussion](https://valgrind.org/docs/manual/cg-manual.html#cg-manual.sim-details) for context on why simplified cache models do not reproduce modern processor performance; this project does not invoke or depend on Valgrind.

## Attribution

Created with substantial AI assistance using OpenAI Codex. These are educational implementations and simulations; the repository's tests document the behavior that was verified.
