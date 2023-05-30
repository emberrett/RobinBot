import unittest
import example_config
from robin_bot import RobinBot, RobinCryptoBot


class TestRetrievalMethods(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.robin_bot = RobinBot(**example_config.config, sandbox=True)

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

    def test_get_top_n_stocks(self):
        self.assertIsInstance(self.robin_bot.get_top_n_stocks(15), list)

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

    def test_buy_from_top_stocks(self):
        purchase_results = self.robin_bot.buy_from_top_stocks(buy_limit=5)
        print(purchase_results)
        self.assertIsInstance(purchase_results, list)

    def test_sell_portfolio(self):
        sell_results = self.robin_bot.sell_portfolio()
        print(sell_results)
        self.assertIsInstance(sell_results, list)

# class TestCryptoRetrievalMethods(TestRetrievalMethods):

#     def __init__(self, methodName: str = "runTest") -> None:
#         super().__init__(methodName)
#         self.robin_bot = RobinCryptoBot(**example_config.config, sandbox=True)
#     test_symbol = 'BTC'
#     test_symbol_list = example_config.config["crypto_watchlist"]

#     def test_get_top_n_stocks(self):
#         pass

#     def test_buy_from_top_stocks(self):
#         pass

#     def test_buy_from_list(self):
#         purchase_results = self.robin_bot.buy_from_ticker_list(
#             self.test_symbol_list)
#         print(purchase_results)
#         self.assertIsInstance(purchase_results, list)


if __name__ == '__main__':
    unittest.main()
