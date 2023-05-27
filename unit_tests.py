import unittest
import example_config
from robin_bot import RobinBot, RobinCryptoBot


class TestRetrievalMethods(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.robin_bot = RobinBot(**example_config.config)

    test_symbol = 'AAPL'
    test_symbol_list = ['AAPL', 'AMZN', 'GOOGL']

    def setUp(self) -> None:
        self.robin_bot.login()

    def tearDown(self):
        self.robin_bot.logout()

    def test_get_portfolio_symbols(self):
        self.assertIsInstance(self.robin_bot.get_portfolio_symbols(), list)

    def test_get_average_cost(self):
        portfolio_ticker_symbol = self.robin_bot.get_portfolio_symbols()[0]
        self.assertIsInstance(self.robin_bot.get_average_cost(
            portfolio_ticker_symbol), float)

    def test_get_historical_prices(self):
        self.assertIsInstance(
            self.robin_bot.get_historical_prices(self.test_symbol_list), list)

    def test_get_current_price(self):
        self.assertIsInstance(
            self.robin_bot.get_current_price(self.test_symbol), float)

    def test_get_price_change(self):
        self.assertIsInstance(
            self.robin_bot.get_price_change(self.test_symbol), float)

    def test_get_price_changes(self):
        self.assertIsInstance(self.robin_bot.get_price_changes(
            self.test_symbol_list), dict)

    def test_get_top_n_market_movers(self):
        self.assertIsInstance(self.robin_bot.get_top_n_market_movers(), list)

    def test_sort_top_movers(self):
        top_n_market_movers = self.robin_bot.get_top_n_market_movers(15)

        first_negative_ticker = next(
            iter(self.robin_bot.sort_top_movers(top_n_market_movers, False).values()))
        self.assertLess(first_negative_ticker, 0)

        first_positive_ticker = next(
            iter(self.robin_bot.sort_top_movers(top_n_market_movers).values()))
        self.assertGreater(first_positive_ticker, 0)

    def test_get_symbol_equity(self):
        portfolio_ticker_symbol = self.robin_bot.get_portfolio_symbols()[0]
        self.assertIsInstance(self.robin_bot.get_symbol_equity(
            portfolio_ticker_symbol), float)

    def test_get_total_equity(self):
        self.assertIsInstance(self.robin_bot.get_total_equity(), float)

    def test_get_shares(self):
        portfolio_ticker_symbol = self.robin_bot.get_portfolio_symbols()[0]
        self.assertIsInstance(self.robin_bot.get_shares(
            portfolio_ticker_symbol), float)

    def test_get_total_in_robinhood(self):
        self.assertIsInstance(self.robin_bot.get_total_in_robinhood(), float)


class TestCryptoRetrievalMethods(TestRetrievalMethods):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.robin_bot = RobinCryptoBot(**example_config.config)

    test_symbol = 'BTC'
    test_symbol_list = ['BTC']


if __name__ == '__main__':
    unittest.main()
