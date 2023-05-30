config = {
    # Determines whether a stock should not be bought if its currentPrice/52WeekHigh ratio dips below the given threshold
    "avoid_year_threshold": 0.30,
    # Sets the lowest amount (in dollars) you can spend on a single order
    "buy_dollar_limit": 1,
    # TODO: provide explanation
    "buy_threshold": 1,
    # Sets a limit on how much of your buying power you can use at one time
    "buying_power_limit": 0.1,
    # Determines whether stock shouldn't be bought if its currentPrice/52WeekHigh ratio goes above the given threshold
    "buy_year_threshold": .95,
    # No current method for getting top movers for crypto (like we can for normal stocks),
    # So we provide static list of cryptos to watch
    "crypto_watchlist": ['BTC', 'DOGE', 'ETC', 'BSV', 'BCH', 'LTC', 'ETC', 'ETH'],
    # the data point of a stock to run analysis on. Options are open_price, close_price, high_price, and low_price
    "data_point": "close_price",
    # Sets the interval for historical stock data that is retrieved.
    # Available options are '5minute', '10minute', 'hour', 'day', and 'week'. Interval must be less than span
    "interval": "day",
    # Sets the span for historical stock data that is retrieved when determining movement
    # Available options are day, week, month, 3month, year, or 5year. Span must be greater than interval.
    "span": "week",
    # Limits how much a stock can be bought for if the purchase total is greater than its percentage of your portfolio
    "portfolio_buy_threshold": .1,
    # Limits how much a stock can be sold for if the sale total is greater than its percentage of your portfolio
    "portfolio_sell_threshold": 1,
    # Determines how much profit must be made as percentage of average buy price before sale can be executed
    "profit_threshold": .15,
    # Determines how small (in dollars) a single sale can be
    "sell_dollar_limit": 1,
    # The max number of sell transactions that can occur when selling multiple symbols at once
    "sell_limit": 10,
    # When set to True, allows you to sell portions of stocks (not all Robinhood accounts are allowed to do this)
    "sell_fractional": True,
    # Determines whether stock shouldn't be bought if its currentPrice/52WeekHigh ratio goes above the given threshold
    "sell_year_threshold": 1,
}
