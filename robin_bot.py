import robin_stocks.robinhood as rs
import os
import pyotp
from dotenv import load_dotenv


class RobinBot:
    def __init__(self, sandbox=False, **kwargs):

        self.interval = kwargs["interval"]
        self.span = kwargs["span"]
        self.data_point = kwargs["data_point"]
        self.avoid_year_threshold = kwargs["avoid_year_threshold"]
        self.buy_dollar_limit = kwargs["buy_dollar_limit"]
        self.buy_threshold = kwargs["buy_threshold"]
        self.buy_year_threshold = kwargs["buy_year_threshold"]
        self.buying_power_limit = kwargs["buying_power_limit"]
        self.crypto_watchlist = kwargs["crypto_watchlist"]
        self.data_point = kwargs["data_point"]
        self.interval = kwargs["interval"]
        self.portfolio_buy_threshold = kwargs["portfolio_buy_threshold"]
        self.portfolio_sell_threshold = kwargs["portfolio_sell_threshold"]
        self.profit_threshold = kwargs["profit_threshold"]
        self.sell_dollar_limit = kwargs["sell_dollar_limit"]
        self.sell_limit = kwargs["sell_limit"]
        self.sell_fractional = kwargs["sell_fractional"]
        self.sell_year_threshold = kwargs["sell_year_threshold"]
        self.span = kwargs["span"]
        self.sandbox = sandbox  # won't actually execute orders if set to True
        self.total_in_robinhood = None

    def login(self):
        load_dotenv()
        robin_user = os.environ["ROBINHOOD_USERNAME"]
        robin_pass = os.environ["ROBINHOOD_PASSWORD"]
        auth_app = os.environ['ROBINHOOD_AUTH']
        totp = pyotp.TOTP(auth_app).now()
        return rs.login(username=robin_user, password=robin_pass, mfa_code=totp, store_session=False)

    def logout(self):
        rs.logout()

    def cancel_all_orders(self):
        rs.orders.cancel_all_stock_orders()

    def sell_portfolio(self):
        ticker_list = self.get_portfolio_symbols()
        index = 1
        results = []

        self.total_in_robinhood = self.get_total_in_robinhood()

        for ticker in ticker_list:

            if index > self.sell_limit:
                results.append("Max number of stock sales reached.")
                return results
            index += 1
            result = self.sell_with_conditions(
                ticker)
            result = f"Sell {ticker} result: {result}"
            results.append(result)

        if not results:
            return "No options to sell."
        return results

    def sell_with_conditions(self, ticker_symbol):

        if self.total_in_robinhood is None:
            self.total_in_robinhood = self.get_total_in_robinhood()

        current_shares = self.get_shares(ticker_symbol)
        if current_shares == 0:
            return "No shares available for sale."

        average_cost = self.get_average_cost(ticker_symbol)
        current_price = self.get_current_price(ticker_symbol)
        profit = (current_price - average_cost) / average_cost

        if profit < self.profit_threshold:
            return f"Profit of sale does not meet profit threshold. ({'{:.2%}'.format(profit)})"

        year_high = self.get_52_week_high(ticker_symbol)

        if current_price / year_high > self.sell_year_threshold:
            return "Proximity to 52 week high exceeds threshold. Price: " + str(
                current_price) + " 52-week high: " + str(year_high)

        sell_amount = self.get_symbol_equity(ticker_symbol)
        current_equity = sell_amount

        if sell_amount == 0 or self.sell_fractional is False:
            return self.sell(current_shares, ticker_symbol, True)

        if sell_amount / self.total_in_robinhood > self.portfolio_sell_threshold:
            sell_amount = self.portfolio_sell_threshold * self.total_in_robinhood

        # if sale amount < dollar limit, sell as shares as opposed to price to avoid $1 sale restriction
        if sell_amount < self.sell_dollar_limit:
            sell_amount = sell_amount / current_price
            if sell_amount > current_shares:
                sell_amount = current_shares
            return self.sell(sell_amount, ticker_symbol, True)

        # if equity - sale amount < the dollar limit, sell all shares
        if abs(current_equity - sell_amount) < self.sell_dollar_limit:
            return self.sell(current_shares, ticker_symbol, True)
        return self.sell(sell_amount, ticker_symbol)

    def sell(self, sell_amount, ticker_symbol, shares=False):
        if self.sandbox:
            return f"Sandbox mode enabled. Simulated sell amount for {ticker_symbol} is ${sell_amount}"
        if shares:
            result = rs.orders.order_sell_fractional_by_quantity(
                ticker_symbol, round(sell_amount, 6))
            return result
        result = rs.orders.order_sell_fractional_by_price(
            ticker_symbol, sell_amount)

        if result.get('detail') == 'Not enough shares to sell.':
            total_shares = self.get_shares(ticker_symbol)
            result = rs.orders.order_sell_fractional_by_quantity(
                ticker_symbol, total_shares)
            return result
        return result

    def buy_from_top_stocks(self, buy_limit=None,
                            include_stocks_in_portfolio=False):

        portfolio_symbols = self.get_portfolio_symbols(
        ) if include_stocks_in_portfolio else []

        top_stock_limit = 100 if not buy_limit else buy_limit
        top_stocks = self.get_top_n_stocks(top_stock_limit)
        negative_price_changes_for_top_stocks = {
            k: v for k, v in self.get_price_changes(top_stocks, descending=True).items() if v < 0}

        if not include_stocks_in_portfolio:
            elligible_stocks = {key: value for key, value in negative_price_changes_for_top_stocks.items(
            ) if key not in portfolio_symbols}
        else:
            elligible_stocks = negative_price_changes_for_top_stocks

        if not elligible_stocks:
            return "No negative change for given stocks."

        self.total_in_robinhood = self.get_total_in_robinhood()

        results = []
        index = 1
        for key in elligible_stocks:

            if buy_limit:
                if index > buy_limit:
                    result = f"Max number of stock purchases reached ({buy_limit})"
                    results.append(result)
                    return results

            result = self.buy_with_conditions(key)
            result = f"Buy {key} result: {result}"
            results.append(result)
            index += 1

        return results

    def buy_from_ticker_list(self, ticker_list):
        results = []
        for ticker in ticker_list:
            results.append(self.buy_with_conditions(ticker))
        return results

    def buy_with_conditions(self, ticker_symbol):

        if self.total_in_robinhood is None:
            self.total_in_robinhood = self.get_total_in_robinhood()

        buying_power = self.get_buying_power()
        buy_amount = buying_power * self.buying_power_limit
        price_change = self.get_price_change(ticker_symbol)
        current_price = self.get_current_price(ticker_symbol)
        year_high = self.get_52_week_high(ticker_symbol)

        if buying_power < self.buy_dollar_limit:
            return f"Buying power less than dollar limit ({buying_power})"

        # check if purchase takes up too much of portfolio
        if buy_amount / self.total_in_robinhood > self.portfolio_buy_threshold:
            buy_amount = self.portfolio_buy_threshold * self.total_in_robinhood

        if buy_amount / buying_power > self.buying_power_limit:
            buy_amount = buying_power * self.buying_power_limit

        if buy_amount < self.buy_dollar_limit:
            buy_amount = self.buy_dollar_limit

        if price_change < self.buy_threshold:
            if current_price / year_high > self.avoid_year_threshold:
                if current_price / year_high < self.buy_year_threshold:
                    return self.buy(ticker_symbol=ticker_symbol, buy_amount=buy_amount)
                else:
                    return f"Price too close to 52-week high threshold. Price: {current_price}. 52-week high: {year_high}"
            else:
                return f"Price too far from 52-week high threshold. Price: {current_price}. 52-week high: {year_high}"
        else:
            return f"Price decrease lower than buy threshold. ({'{:.2%}'.format(price_change)})"

    def buy(self, ticker_symbol, buy_amount):
        if self.sandbox:
            return f"Sandbox mode enabled. Simulated buy amount for {ticker_symbol} is ${buy_amount}"
        result = rs.orders.order_buy_fractional_by_price(
            ticker_symbol, buy_amount)
        if result.get('detail') is not None:
            while 'You can only purchase' in result.get(
                    'detail'):
                buy_amount = buy_amount * .90
                if buy_amount < self.buy_dollar_limit:
                    return "Fraction too small to purchase (" + str(buy_amount) + ")"
            result = rs.orders.order_buy_fractional_by_price(
                ticker_symbol, buy_amount)

        return result

    def get_portfolio_symbols(self):
        portfolio_items = rs.account.build_holdings()
        ticker_symbols = list(portfolio_items.keys())
        return ticker_symbols

    def get_average_cost(self, ticker_symbol):
        return float((rs.account.build_holdings().get(ticker_symbol)).get('average_buy_price'))

    def get_historical_prices(self, ticker_symbol):
        return rs.stocks.get_stock_historicals(ticker_symbol, interval=self.interval, span=self.span)

    def get_current_price(self, ticker_symbol):
        return float(rs.markets.get_stock_quote_by_symbol(ticker_symbol).get('last_trade_price'))

    def get_price_change(self, ticker_symbol):
        stock_historical_prices = self.get_historical_prices(ticker_symbol)
        first_price = float(stock_historical_prices[0].get(self.data_point))
        current_price = self.get_current_price(ticker_symbol)
        return (current_price - first_price) / first_price

    def get_price_changes(self, ticker_list, descending=False):
        price_changes = {}
        for ticker in ticker_list:
            price_changes[ticker] = self.get_price_change(ticker)
        return {k: v for k, v in sorted(price_changes.items(), key=lambda item: item[1], reverse=descending)}

    def get_top_n_stocks(self, limit=100):
        if limit > 100:
            raise Exception("Limit for top n movers is 100.")
        ticker_list = rs.markets.get_top_100(info='symbol')
        ticker_list = ticker_list[:limit]
        return ticker_list

    def get_symbol_equity(self, ticker_symbol):
        portfolio_items = rs.account.build_holdings()
        return float((portfolio_items.get(ticker_symbol)).get('equity'))

    def get_total_equity(self):
        stock_portfolio_dict = rs.account.build_holdings()
        portfolioEquity = 0
        for value in stock_portfolio_dict.values():
            portfolioEquity += (float(value.get('equity')))
        return portfolioEquity

    def get_shares(self, ticker_symbol):
        portfolio_items = rs.account.build_holdings()
        return float((portfolio_items.get(ticker_symbol)).get('quantity'))

    def get_buying_power(self):
        return float(rs.profiles.load_account_profile(info='buying_power'))

    def get_total_invested(self):
        return self.get_buying_power() + self.get_total_equity()

    def get_total_in_robinhood(self):
        return self.get_buying_power() + self.get_total_invested()

    def get_52_week_high(self, ticker_symbol):
        return float(rs.stocks.get_fundamentals(ticker_symbol, info='high_52_weeks')[0])


class RobinCryptoBot(RobinBot):
    def __init__(self, **kwargs):
        # robin_stocks does not currently support getting top movers for crypto, so I need to set ones to watch manually
        self.crypto_watchlist = kwargs["crypto_watchlist"]
        super().__init__(**kwargs)

    def sell(self, sell_amount, ticker_symbol, shares=False):
        if shares:
            result = rs.orders.order_sell_crypto_by_quantity(
                ticker_symbol, round(sell_amount, 8))
            return result

        result = rs.orders.order_sell_crypto_by_price(
            ticker_symbol, sell_amount)

        if result.get('non_field_errors') == ['Insufficient holdings.']:
            total_shares = self.get_shares(ticker_symbol)
            result = rs.orders.order_sell_crypto_by_quantity(
                ticker_symbol, total_shares)
            return result

        return result

    def buy_from_top_stocks(self):
        raise NotImplementedError(
            "buy_from_top_stocks not available for RobinCryptoBot.")

    def get_portfolio_symbols(self):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        crypto_portfolio_symbol_list = []
        for x in crypto_portfolio_items:
            if float(x['cost_bases'][0]['direct_cost_basis']) > 0:
                crypto_symbol = (x.get('currency')).get('code')
                if crypto_symbol != 'USD':
                    crypto_portfolio_symbol_list.append(crypto_symbol)
            return crypto_portfolio_symbol_list

    def get_crypto_portfolio_and_watchlist_symbols(self):
        return (set(self.crypto_watchlist.extend(self.get_portfolio_symbols())))

    def get_average_cost(self, ticker_symbol):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code == ticker_symbol:
                costBasis = float((crypto_portfolio_items[i].get(
                    'cost_bases')[0]).get('direct_cost_basis'))
                quantity = float((crypto_portfolio_items[i].get(
                    'cost_bases')[0]).get('direct_quantity'))
                return costBasis / quantity

    def get_historical_prices(self, ticker_symbol):
        return rs.crypto.get_crypto_historicals(ticker_symbol, interval=self.interval, span=self.span)

    def get_current_price(self, ticker):
        return float(rs.crypto.get_crypto_quote(ticker, info='mark_price'))

    def get_symbol_equity(self, ticker_symbol):
        if ticker_symbol in self.get_portfolio_symbols():
            return self.get_symbol_equity(ticker_symbol)
        else:
            raise Exception("Symbol is not in portfolio.")

    def get_portfolio_equity(self):
        crypto_ticker_dict = {}
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code != 'USD':
                crypto_ticker_dict[code] = float(
                    self.get_symbol_equity(code))
        return crypto_ticker_dict

    def get_total_equity(self):
        return sum(self.get_portfolio_equity().values())

    def get_symbol_equity(self, ticker_symbol):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code == ticker_symbol:
                quantity = float((crypto_portfolio_items[i].get(
                    'cost_bases')[0]).get('direct_quantity'))
                return quantity * self.get_current_price(code)

    def get_shares(self, ticker_symbol):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code == ticker_symbol:
                quantity = float((crypto_portfolio_items[i].get(
                    'cost_bases')[0]).get('direct_quantity'))
                return quantity

    def get_52_week_high(self, ticker_symbol):
        return float(max(rs.crypto.get_crypto_historicals(ticker_symbol, 'day', 'year', info='high_price')))
