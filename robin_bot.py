import robin_stocks.robinhood as rs
import os
import pyotp


class RobLogin:

    def login(self):
        robin_user = os.environ["robinhood_username"]
        robin_pass = os.environ["robinhood_password"]
        auth_app = os.environ['robinhood_auth']
        totp = pyotp.TOTP(auth_app).now()
        return rs.login(username=robin_user, password=robin_pass, mfa_code=totp, store_session=False)

    # Update Session data with authorization or raise exception with the information present in data.
    def logout(self):
        rs.logout()


class RobRetriever:
    def __init__(self, crypto_watchlist, interval, span, data_point):
        # robin_stocks does not currently support getting top movers for crypto, so I need to set ones to watch manually
        self.crypto_watchlist = crypto_watchlist
        self.interval = interval
        self.span = span
        self.data_point = data_point

    def get_portfolio_symbols(self, include_crypto=True):
        portfolio_items = rs.account.build_holdings()
        ticker_symbols = list(portfolio_items.keys())
        if include_crypto:
            crypto_symbol_list = self.get_portfolio_crypto_symbols()
            for x in crypto_symbol_list:
                ticker_symbols.append(x)
        return ticker_symbols

    def get_portfolio_crypto_symbols(self):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        crypto_portfolio_symbol_list = []
        for x in crypto_portfolio_items:
            if float(x['cost_bases'][0]['direct_cost_basis']) > 0:
                crypto_symbol = (x.get('currency')).get('code')
                if crypto_symbol != 'USD':
                    crypto_portfolio_symbol_list.append(crypto_symbol)
            return crypto_portfolio_symbol_list

    def get_crypto_list(self):
        crypto_list = self.crypto_watchlist
        crypto_portfolio_symbols = self.get_portfolio_crypto_symbols()
        for x in crypto_portfolio_symbols:
            if x not in crypto_list:
                crypto_list.append(x)
        return crypto_list

    def get_average_cost(self, ticker_symbol):
        if ticker_symbol in self.get_crypto_list():
            return self.get_crypto_average_cost(ticker_symbol)
        else:
            return float((rs.account.build_holdings().get(ticker_symbol)).get('average_buy_price'))

    def get_crypto_average_cost(self, ticker_symbol):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code == ticker_symbol:
                costBasis = float((crypto_portfolio_items[i].get('cost_bases')[0]).get('direct_cost_basis'))
                quantity = float((crypto_portfolio_items[i].get('cost_bases')[0]).get('direct_quantity'))
                return costBasis / quantity

    def get_historical_prices(self, ticker_symbol):
        if ticker_symbol in self.get_crypto_list():
            stock_historical_prices = rs.crypto.get_crypto_historicals(ticker_symbol, interval=self.interval, span=self.span)
        else:
            stock_historical_prices = rs.stocks.get_stock_historicals(ticker_symbol, interval=self.interval, span=self.span)
        return stock_historical_prices

    def get_current_price(self, ticker_symbol):
        if ticker_symbol in self.get_crypto_list():
            return self.get_current_crypto_price(ticker_symbol)
        return float(rs.markets.get_stock_quote_by_symbol(ticker_symbol).get('last_trade_price'))

    def get_current_crypto_price(self, ticker):
        return float(rs.crypto.get_crypto_quote(ticker, info='mark_price'))

    def get_price_change(self, ticker_symbol):
        stock_historical_prices = self.get_historical_prices(ticker_symbol)
        first_price = float(stock_historical_prices[0].get(self.data_point))
        current_price = self.get_current_price(ticker_symbol)
        return (current_price - first_price) / first_price

    def get_multiple_price_changes(self, ticker_list):
        mover_data = {}
        for x in ticker_list:
            mover_data[x] = self.get_price_change(x)
        return mover_data

    def get_top_100_market_movers(self, limit=100):
        # get top 100 movers on Robinhood and pass them to a list
        ticker_list = rs.markets.get_top_100(info='symbol')
        ticker_list = ticker_list[:limit]
        return ticker_list

    def combine_top_movers_with_crypto(self):
        top_movers = self.get_top_100_market_movers()
        top_movers.extend(self.get_crypto_list())
        return top_movers

    def sort_top_movers(self, ticker_list, positive=True):
        ticker_price_change_dict = self.get_multiple_price_changes(ticker_list)
        single_sided_ticker_dict = {}
        if positive:
            single_sided_ticker_dict = dict(reversed(sorted(ticker_price_change_dict.items(), key=lambda item: item[1])))
            for key, value in single_sided_ticker_dict.items():
                if value > 0:
                    single_sided_ticker_dict[key] = value
            return single_sided_ticker_dict
        single_sided_ticker_dict = dict((sorted(ticker_price_change_dict.items(), key=lambda item: item[1])))
        for key, value in single_sided_ticker_dict.items():
            if value < 0:
                single_sided_ticker_dict[key] = value
        return single_sided_ticker_dict

    def get_symbol_equity(self, ticker_symbol):
        portfolio_items = rs.account.build_holdings()
        if ticker_symbol in self.get_crypto_list():
            return self.get_single_crypto_equity(ticker_symbol)
        return float((portfolio_items.get(ticker_symbol)).get('equity'))

    def get_crypto_portfolio_equity(self):
        crypto_ticker_dict = {}
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code != 'USD':
                crypto_ticker_dict[code] = float(self.get_single_crypto_equity(code))
        return crypto_ticker_dict

    def get_total_crypto_equity(self):
        return sum(self.get_crypto_portfolio_equity().values())

    def get_total_equity(self, include_crypto=True):
        stock_portfolio_dict = rs.account.build_holdings()
        portfolioEquity = 0
        for key, value in stock_portfolio_dict.items():
            portfolioEquity += (float(value.get('equity')))
        if include_crypto:
            return portfolioEquity + self.get_total_crypto_equity()
        return portfolioEquity

    def get_single_crypto_equity(self, ticker_symbol):
        crypto_portfolio_items = rs.crypto.get_crypto_positions()
        for i, x in enumerate(crypto_portfolio_items):
            code = (x.get('currency')).get('code')
            if code == ticker_symbol:
                quantity = float((crypto_portfolio_items[i].get('cost_bases')[0]).get('direct_quantity'))
                return quantity * self.get_current_crypto_price(code)

    def getShares(self, ticker_symbol):
        if ticker_symbol in self.get_crypto_list():
            crypto_portfolio_items = rs.crypto.get_crypto_positions()
            for i, x in enumerate(crypto_portfolio_items):
                code = (x.get('currency')).get('code')
                if code == ticker_symbol:
                    quantity = float((crypto_portfolio_items[i].get('cost_bases')[0]).get('direct_quantity'))
                    return quantity
        else:
            portfolio_items = rs.account.build_holdings()
            if ticker_symbol in self.get_crypto_list():
                return self.get_crypto_shares(ticker_symbol)
            return float((portfolio_items.get(ticker_symbol)).get('quantity'))

    def get_buying_power(self):
        return float(rs.profiles.load_account_profile(info='buying_power'))

    def get_total_invested(self, include_crypto=True):
        return self.get_buying_power() + self.get_total_equity(include_crypto=include_crypto)

    def get_total_in_robinhood(self):
        return self.get_buying_power() + self.get_total_invested()


    def get_52_week_high(self, ticker_symbol):
        if ticker_symbol in self.get_crypto_list():
            return float(max(rs.crypto.get_crypto_historicals(ticker_symbol, 'day', 'year', info='high_price')))
        return float(rs.stocks.get_fundamentals(ticker_symbol, info='high_52_weeks')[0])


class RobExecutor(RobRetriever):
    def __init__(self, crypto_watchlist, interval, span, data_point, sell_year_threshold,
                 sell_dollar_limit,
                 buy_year_threshold, avoid_year_threshold, buy_threshold, portfolio_sell_threshold,
                 portfolio_buy_threshold, buying_power_limit, buy_dollar_limit, profit_threshold):
        super(RobExecutor, self).__init__(crypto_watchlist, interval, span, data_point)
        self.sell_year_threshold = sell_year_threshold
        self.sell_dollar_limit = sell_dollar_limit
        self.buy_year_threshold = buy_year_threshold
        self.avoid_year_threshold = avoid_year_threshold
        self.buy_threshold = buy_threshold
        self.portfolio_sell_threshold = portfolio_sell_threshold
        self.portfolio_buy_threshold = portfolio_buy_threshold
        self.interval = interval
        self.span = span
        self.crypto_watchlist = crypto_watchlist
        self.data_point = data_point
        self.buying_power_limit = buying_power_limit
        self.buy_dollar_limit = buy_dollar_limit
        self.profit_threshold = profit_threshold

    def sell_portfolio(self, include_crypto=True, only_crypto=False, sell_limit=False,
                      sellFractional=False):
        # get list of portfolio tickers
        if only_crypto:
            ticker_list = self.get_portfolio_crypto_symbols()
        elif include_crypto:
            ticker_list = self.get_portfolio_symbols()
        else:
            ticker_list = self.get_portfolio_symbols(include_crypto=False)
        index = 1
        result_list = []
        total_in_robinhood = self.get_total_in_robinhood()
        for ticker in ticker_list:
            if sell_limit is not False:
                if index > sell_limit:
                    result_item = "Max number of stock sales reached."
                    result_list.append(result_item)
                    return result_list
            index += 1
            result = str(self.sell_with_conditions(ticker, total_invested=total_in_robinhood, sellFractional=sellFractional))
            result_item = str('Sell ' + ticker + ' Result: ' + result)
            result_list.append(result_item)
        if not result_list:
            result_list.append("No options to sell.")
        return result_list

    def sell_with_conditions(self, ticker_symbol, total_invested, sellFractional=False):
        current_shares = self.getShares(ticker_symbol)
        if current_shares == 0:
            return "No shares available for sale."
        average_cost = self.get_average_cost(ticker_symbol)
        current_price = self.get_current_price(ticker_symbol)
        # check to see if profit meets threshold
        profit = (current_price - average_cost) / average_cost
        if profit < self.profit_threshold:
            return "Profit of sale does not meet profit threshold. (" + "{:.2%}".format(profit) + ")"
        year_high = self.get_52_week_high(ticker_symbol)
        # check that the price isn't too close to the 52-week high
        if current_price / year_high > self.sell_year_threshold:
            return "Proximity to 52 week high exceeds threshold. Price: " + str(
                current_price) + " 52-week high: " + str(year_high)
        sell_amount = self.get_symbol_equity(ticker_symbol)
        current_equity = sell_amount

        # sell all shares of stock if sellFractional is false
        if sell_amount == 0 or sellFractional is False:
            return self.sell(current_shares, ticker_symbol, True)

        # if sale account for more than certain % of portfolio, lower the number to the max % of portfolio
        if sell_amount / total_invested > self.portfolio_sell_threshold:
            sell_amount = self.portfolio_sell_threshold * total_invested

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
        if ticker_symbol in self.get_crypto_list():
            if shares:
                result = rs.orders.order_sell_crypto_by_quantity(ticker_symbol, round(sell_amount, 8))
                return result
            result = rs.orders.order_sell_crypto_by_price(ticker_symbol, sell_amount)
            if result.get('non_field_errors') == ['Insufficient holdings.']:
                total_shares = self.get_crypto_shares(ticker_symbol)
                result = rs.orders.order_sell_crypto_by_quantity(ticker_symbol, total_shares)
                return result
            return result

        if ticker_symbol not in self.get_crypto_list():
            if shares:
                result = rs.orders.order_sell_fractional_by_quantity(ticker_symbol, round(sell_amount, 6))
                return result
            result = rs.orders.order_sell_fractional_by_price(ticker_symbol, sell_amount)
            if result.get('detail') == 'Not enough shares to sell.':
                total_shares = self.getShares(ticker_symbol)
                result = rs.orders.order_sell_fractional_by_quantity(ticker_symbol, total_shares)
                return result
        return result

    def buy_from_market(self, include_crypto=True, only_crypto=False, buy_limit=False,
                      exclude_portfolio_items=True):
        robinhood_total = self.get_total_in_robinhood()
        portfolio_symbols = []
        if exclude_portfolio_items:
            portfolio_symbols = self.get_portfolio_symbols(include_crypto=include_crypto)
        if only_crypto:
            market_dict = self.sort_top_movers(self.get_crypto_list(), False).items()
        elif include_crypto:
            market_dict = self.sort_top_movers(self.combine_top_movers_with_crypto(), False).items()
        else:
            market_dict = self.sort_top_movers(self.get_top_100_market_movers(), False).items()
        result_list = []
        index = 1
        if not market_dict:
            return "No negative change for given symbols."
        for key, value in market_dict:
            """
            buy stock if the price change is below the buy threshold and current price is not too close to the 52 week
            high and if the stock is not under a certain amount as a percentage of its 52 week high
            """
            if buy_limit is not False:
                if index > buy_limit:
                    result_item = "Max number of stock purchases reached. (" + str(buy_limit) + ")"
                    result_list.append(result_item)
                    return result_list
            result = str(self.buy_with_conditions(key, robinhood_total, portfolio_symbols=portfolio_symbols))
            result_item = str('Buy ' + key + ' Result: ' + result)
            result_list.append(result_item)
            index += 1
        return result_list

    # change so that we don't buy tickers we already have in our portfolio
    def buy_with_conditions(self, ticker_symbol, total_invested, portfolio_symbols=[]):
        if ticker_symbol in portfolio_symbols:
            return "Symbol already in portfolio."
        buying_power = self.get_buying_power()
        buying_power_limit = self.buying_power_limit
        portfolio_buy_threshold = self.portfolio_buy_threshold
        buy_amount = buying_power * buying_power_limit
        price_change = self.get_price_change(ticker_symbol)
        current_price = self.get_current_price(ticker_symbol)
        year_high = self.get_52_week_high(ticker_symbol)
        if buying_power < self.buy_dollar_limit:
            return "Buying power less than dollar limit. (" + str(buying_power) + ")"
        # check if purchase takes up too much of portfolio
        if buy_amount / total_invested > portfolio_buy_threshold:
            buy_amount = portfolio_buy_threshold * total_invested
        # check if buy amount is greater than buying power limit
        if buy_amount / buying_power > buying_power_limit:
            buy_amount = buying_power * buying_power_limit
        # if buy amount is less than dollar limit, set buy amount to dollar
        if buy_amount < self.buy_dollar_limit:
            buy_amount = self.buy_dollar_limit
        if price_change < self.buy_threshold:
            if current_price / year_high > self.avoid_year_threshold:
                if current_price / year_high < self.buy_year_threshold:
                    return self.buy(ticker_symbol=ticker_symbol, buy_amount=buy_amount)
                else:
                    return "Price too close to 52-week high threshold. Price: " + str(
                        current_price) + " 52-week high: " + str(year_high)
            else:
                return "Price too far from 52-week high threshold. Price: " + str(
                    current_price) + " 52-week high: " + str(year_high)
        else:
            return "Price decrease lower than buy threshold. (" + "{:.2%}".format(price_change) + ")"

    def buy(self, ticker_symbol, buy_amount):
        if ticker_symbol in self.get_crypto_list():
            result = rs.orders.order_buy_crypto_by_price(ticker_symbol, buy_amount)
            while result.get('non_field_errors') == ['Insufficient holdings.']:
                buy_amount = buy_amount * .90
                if buy_amount < self.buy_dollar_limit:
                    return "Fraction too small to purchase (" + str(buy_amount) + ")"
                result = rs.orders.order_buy_crypto_by_price(ticker_symbol, buy_amount)
        if ticker_symbol not in self.get_crypto_list():
            result = rs.orders.order_buy_fractional_by_price(ticker_symbol, buy_amount)
            if result.get('detail') is not None:
                while 'You can only purchase' in result.get(
                        'detail'):
                    buy_amount = buy_amount * .90
                    if buy_amount < self.buy_dollar_limit:
                        return "Fraction too small to purchase (" + str(buy_amount) + ")"
                result = rs.orders.order_sell_fractional_by_price(ticker_symbol, buy_amount)
        return result
