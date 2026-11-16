import unittest

from tests import helpers  # noqa: F401
from kitrader.broker import BrokerError, Portfolio


class BrokerTests(unittest.TestCase):
    def test_buy_and_sell_with_fees(self):
        pf = Portfolio(20.0, 0.004)
        buy = pf.buy(1.0, 60000.0, 18.0)
        self.assertAlmostEqual(buy["btc"], 0.0003, places=8)
        self.assertAlmostEqual(buy["invested_eur"], 18.0, places=6)
        self.assertAlmostEqual(buy["fee_eur"], 0.072, places=6)
        self.assertAlmostEqual(pf.cash, 20.0 - 18.0 - 0.072, places=6)
        self.assertAlmostEqual(pf.equity(60000.0), 20.0 - 0.072, places=6)

        sell = pf.sell(2.0, 61200.0)                      # +2 %
        gross = 0.0003 * 61200.0
        self.assertAlmostEqual(sell["proceeds_eur"], gross, places=6)
        self.assertAlmostEqual(sell["fee_eur"], gross * 0.004, places=6)
        expected_pnl = gross * 0.996 - 18.072
        self.assertAlmostEqual(sell["pnl_eur"], expected_pnl, places=6)
        self.assertAlmostEqual(pf.cash, 20.0 + expected_pnl, places=6)
        self.assertEqual(pf.btc, 0.0)
        self.assertIsNone(pf.position)
        self.assertAlmostEqual(pf.fees_total, 0.072 + gross * 0.004, places=6)

    def test_round_trip_at_same_price_loses_exactly_the_fees(self):
        pf = Portfolio(20.0, 0.004)
        pf.buy(1.0, 50000.0, 10.0)
        sell = pf.sell(2.0, 50000.0)
        self.assertAlmostEqual(sell["pnl_eur"], -(10.0 * 0.004) * 2, places=6)

    def test_no_leverage(self):
        pf = Portfolio(20.0, 0.004)
        with self.assertRaises(BrokerError):
            pf.buy(1.0, 60000.0, 20.0)                    # 20 EUR + Gebuehr > Guthaben
        with self.assertRaises(BrokerError):
            pf.buy(1.0, 60000.0, 25.0)                    # mehr als Startkapital
        self.assertEqual(pf.cash, 20.0)

    def test_stake_never_above_start_capital_even_with_profits(self):
        pf = Portfolio(20.0, 0.004)
        pf.cash = 40.0                                    # angenommene fruehere Gewinne
        with self.assertRaises(BrokerError):
            pf.buy(1.0, 60000.0, 30.0)

    def test_no_short_selling_and_single_position(self):
        pf = Portfolio(20.0, 0.004)
        with self.assertRaises(BrokerError):
            pf.sell(1.0, 60000.0)
        pf.buy(1.0, 60000.0, 10.0)
        with self.assertRaises(BrokerError):
            pf.buy(2.0, 60000.0, 5.0)

    def test_state_round_trip(self):
        pf = Portfolio(20.0, 0.004)
        pf.buy(1.0, 60000.0, 18.0, "Kraken")
        pf.position.peak_price = 60500.0
        restored = Portfolio.from_dict(pf.to_dict())
        self.assertEqual(restored.to_dict(), pf.to_dict())
        self.assertEqual(restored.position.peak_price, 60500.0)


if __name__ == "__main__":
    unittest.main()
