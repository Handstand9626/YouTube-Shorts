import unittest

from tests import helpers  # noqa: F401  (setzt den Importpfad)
from kitrader import indicators as ind

# Bekanntes Lehrbuchbeispiel fuer den RSI (14) nach Wilder
CLOSES = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03,
          45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64, 46.21, 46.25, 45.71, 46.45,
          45.78, 45.35, 44.03, 44.18, 44.22, 44.57, 43.42, 42.66, 43.13]
EXPECTED_RSI = [70.53, 66.32, 66.55, 69.41, 66.36, 57.97, 62.93, 63.26, 56.06, 62.38, 54.71,
                50.42, 39.99, 41.46, 41.87, 45.46, 37.30, 33.08, 37.77]


class IndicatorTests(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(ind.sma([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])

    def test_ema_matches_manual_calculation(self):
        values = [10, 11, 12, 13, 14, 15]
        out = ind.ema(values, 3)
        self.assertEqual(out[:2], [None, None])
        self.assertAlmostEqual(out[2], 11.0)             # SMA der ersten drei Werte
        self.assertAlmostEqual(out[3], 13 * 0.5 + 11 * 0.5)
        self.assertAlmostEqual(out[5], 14.0)

    def test_ema_of_constant_series_is_constant(self):
        self.assertTrue(all(abs(x - 7.0) < 1e-12 for x in ind.ema([7.0] * 60, 20)[19:]))

    def test_rsi_matches_reference_values(self):
        out = ind.rsi(CLOSES, 14)
        self.assertTrue(all(x is None for x in out[:14]))
        # Die Referenzwerte wurden mit ungerundeten Kursen berechnet, die Kurse oben sind
        # auf zwei Stellen gerundet - daher die kleine Toleranz.
        for got, want in zip(out[14:], EXPECTED_RSI):
            self.assertAlmostEqual(got, want, delta=0.1)

    def test_rsi_extremes(self):
        self.assertEqual(ind.rsi(list(range(1, 40)), 14)[-1], 100.0)
        self.assertEqual(ind.rsi(list(range(40, 1, -1)), 14)[-1], 0.0)
        self.assertEqual(ind.rsi([5.0] * 40, 14)[-1], 50.0)

    def test_macd_is_consistent(self):
        values = [100 + (i % 7) * 0.8 + i * 0.3 for i in range(120)]
        line, signal, hist = ind.macd(values)
        fast, slow = ind.ema(values, 12), ind.ema(values, 26)
        self.assertIsNone(line[24])
        self.assertAlmostEqual(line[-1], fast[-1] - slow[-1])
        self.assertIsNone(signal[32])
        self.assertIsNotNone(signal[33])                 # 26 + 9 - 2
        self.assertAlmostEqual(hist[-1], line[-1] - signal[-1])
        self.assertGreater(line[-1], 0)                  # steigende Reihe -> MACD positiv

    def test_too_little_data_gives_none(self):
        self.assertEqual(ind.ema([1, 2], 5), [None, None])
        self.assertEqual(ind.rsi([1, 2, 3], 14), [None, None, None])


if __name__ == "__main__":
    unittest.main()
