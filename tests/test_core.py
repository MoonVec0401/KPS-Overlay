import unittest

from kps_overlay import DEFAULT_CONFIG, IntervalKps, RollingTotalKps, exponential_approach, mix_color, parse_config, segment_for, virtual_key


class CoreTests(unittest.TestCase):
    def test_default_config(self):
        config = parse_config(DEFAULT_CONFIG)
        self.assertEqual(config.keys, ("D", "F", "J", "K"))
        self.assertEqual(config.interval_count, 4)
        self.assertEqual(config.total_kps_window_seconds, 1.0)
        self.assertEqual(config.max_bpm, 240)
        self.assertEqual(segment_for(180, config.segments).color, "#E53935")
        self.assertEqual(segment_for(999, config.segments).color, "#8B1018")

    def test_interval_kps_and_idle_reset(self):
        stats = IntervalKps(["Z", "X"], 0.3)
        stats.press("Z", 9.7)
        stats.press("Z", 9.8)
        stats.press("Z", 10.0)
        stats.press("X", 9.9)
        self.assertAlmostEqual(stats.rates(10.1)["Z"], 1 / 0.15)
        self.assertEqual(stats.rates(10.31), {"Z": 0.0, "X": 0.0})

    def test_press_after_idle_starts_a_new_pair(self):
        stats = IntervalKps(["Z"], 0.3)
        stats.press("Z", 1.0)
        stats.press("Z", 1.5)
        self.assertEqual(stats.rates(1.5)["Z"], 0.0)

    def test_requires_three_presses_for_two_interval_average(self):
        stats = IntervalKps(["Z"], 0.3)
        stats.press("Z", 1.0)
        stats.press("Z", 1.1)
        self.assertEqual(stats.rates(1.1)["Z"], 0.0)
        sample = stats.press("Z", 1.3)
        self.assertAlmostEqual(sample.previous_interval, 0.1)
        self.assertAlmostEqual(sample.latest_interval, 0.2)
        self.assertAlmostEqual(sample.average_interval, 0.15)
        self.assertAlmostEqual(sample.target_kps * 15, 100.0)
        self.assertAlmostEqual(stats.rates(1.3)["Z"], 1 / 0.15)

    def test_configurable_four_interval_average(self):
        stats = IntervalKps(["D"], 0.67, interval_count=4)
        for timestamp in (1.0, 1.1, 1.3, 1.4):
            self.assertEqual(stats.press("D", timestamp).target_kps, 0.0)
        sample = stats.press("D", 1.6)
        self.assertEqual(len(sample.intervals), 4)
        self.assertAlmostEqual(sample.average_interval, 0.15)
        self.assertAlmostEqual(stats.rates(1.6)["D"], 1 / 0.15)

    def test_total_kps_counts_all_presses_in_rolling_second(self):
        total = RollingTotalKps(1.0)
        for timestamp in (9.0, 9.2, 9.6, 10.0):
            total.press(timestamp)
        self.assertEqual(total.rate(10.0), 4.0)
        self.assertEqual(total.rate(10.01), 3.0)

    def test_exponential_approach_reaches_ninety_percent(self):
        self.assertAlmostEqual(exponential_approach(0, 100, 0.2, 0.2), 90.0)

    def test_key_names_and_color_mix(self):
        self.assertEqual(virtual_key("f12"), 0x7B)
        self.assertEqual(virtual_key("control"), 0x11)
        self.assertEqual(mix_color("#FFFFFF", "#000000", 0.5), "#808080")

    def test_rejects_gapped_segments(self):
        data = dict(DEFAULT_CONFIG)
        data["segments"] = [
            {"from_bpm": 0, "to_bpm": 75, "color": "#000000"},
            {"from_bpm": 80, "to_bpm": 100, "color": "#FFFFFF"},
        ]
        with self.assertRaises(ValueError):
            parse_config(data)


if __name__ == "__main__":
    unittest.main()
