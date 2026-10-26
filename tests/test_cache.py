import random
import unittest

from cachelab import Cache, CacheConfig, parse_trace


class CacheTests(unittest.TestCase):
    def outcomes(self, config, addresses):
        cache = Cache(config)
        outcomes = [cache.access(address) for address in addresses]
        return outcomes, cache.report()

    def test_repeated_address_and_line_boundaries(self):
        # Removing line-offset bits is necessary: 0..15 occupy the same line.
        outcomes, report = self.outcomes(CacheConfig(64, 16, 1), [0, 15, 16, 31, 0])
        self.assertEqual(outcomes, [False, True, False, True, True])
        self.assertEqual((report["hits"], report["misses"], report["evictions"]), (3, 2, 0))
        self.assertEqual(report["hit_rate"], 0.6)

    def test_associativity_prevents_direct_mapped_conflicts(self):
        addresses = [0, 64, 0, 64]
        direct, direct_report = self.outcomes(CacheConfig(64, 16, 1), addresses)
        two_way, two_way_report = self.outcomes(CacheConfig(64, 16, 2), addresses)
        self.assertEqual(direct, [False] * 4)
        self.assertEqual(two_way, [False, False, True, True])
        self.assertEqual(direct_report["evictions"], 3)
        self.assertEqual(two_way_report["evictions"], 0)

    def test_lru_hit_refreshes_order_but_fifo_does_not(self):
        addresses = [0, 16, 0, 32, 0]
        lru, _ = self.outcomes(CacheConfig(32, 16, 2, "lru"), addresses)
        fifo, _ = self.outcomes(CacheConfig(32, 16, 2, "fifo"), addresses)
        self.assertEqual(lru, [False, False, True, False, True])
        self.assertEqual(fifo, [False, False, True, False, False])

    def test_fully_associative_capacity_and_eviction(self):
        outcomes, report = self.outcomes(CacheConfig(32, 16, 2), [0, 16, 32, 0])
        self.assertEqual(outcomes, [False, False, False, False])
        self.assertEqual(report["evictions"], 2)

    def test_large_addresses_do_not_lose_tag_bits(self):
        addresses = [2**100, 2**100 + 1, 2**100 + 64, 2**100]
        outcomes, _ = self.outcomes(CacheConfig(64, 16, 1), addresses)
        self.assertEqual(outcomes, [False, True, False, False])

    def test_empty_trace_has_zero_hit_rate(self):
        cache = Cache(CacheConfig(64, 16, 1))
        self.assertEqual(cache.report()["hit_rate"], 0.0)
        self.assertEqual(cache.report()["accesses"], 0)

    def test_invalid_configurations_are_rejected(self):
        for values in [(0, 16, 1), (63, 16, 1), (64, 0, 1), (64, 3, 1),
                       (64, 128, 1), (64, 16, 0), (64, 16, 3), (64, 16, 8)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                CacheConfig(*values)
        with self.assertRaises(ValueError):
            CacheConfig(64, 16, 1, "random")

    def test_invalid_addresses_are_rejected_before_counting(self):
        cache = Cache(CacheConfig(64, 16, 1))
        for address in [-1, 1.5, "16", True]:
            with self.subTest(address=address), self.assertRaises(ValueError):
                cache.access(address)
        self.assertEqual(cache.report()["accesses"], 0)

    def test_seeded_traces_match_independent_timestamp_reference(self):
        # Reference uses timestamps, not production's per-set ordering algorithm.
        rng = random.Random(2026)
        addresses = [rng.randrange(0, 2048) for _ in range(500)]
        for policy in ("lru", "fifo"):
            for ways in (1, 2, 4, 8):
                with self.subTest(policy=policy, ways=ways):
                    config = CacheConfig(128, 16, ways, policy)
                    cache = Cache(config)
                    sets = [{} for _ in range(8 // ways)]
                    hits = evictions = 0
                    for tick, address in enumerate(addresses):
                        block = address // 16
                        bucket = sets[block % len(sets)]
                        expected = block in bucket
                        if expected:
                            hits += 1
                            if policy == "lru":
                                bucket[block] = tick
                        else:
                            if len(bucket) == ways:
                                del bucket[min(bucket, key=bucket.get)]
                                evictions += 1
                            bucket[block] = tick
                        self.assertEqual(cache.access(address), expected)
                    report = cache.report()
                    self.assertEqual(report["hits"], hits)
                    self.assertEqual(report["misses"], 500 - hits)
                    self.assertEqual(report["evictions"], evictions)


class TraceTests(unittest.TestCase):
    def test_decimal_hex_comments_and_blank_lines(self):
        self.assertEqual(list(parse_trace(["# trace", "", "0x10 # hex", "016", "0Xff"])),
                         [16, 16, 255])

    def test_bad_trace_reports_original_line_number(self):
        for invalid in ("-1", "0b10", "1_000", "0xGG", "1 2", "+4"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "line 3:"):
                list(parse_trace(["# comment", "16", invalid]))


if __name__ == "__main__":
    unittest.main()
