import robin_stocks.robinhood as rs
import os


class robLogin:
    def login(self):
        robin_user = os.environ.get("robinhood_username")
        robin_pass = os.environ.get("robinhood_password")
        rs.login(username=robin_user, password=robin_pass, expiresIn=86400, by_sms=True)

    def logout(self):
        rs.logout()


class robRetriever:
    def __init__(self, cryptoWatchList, interval, span, dataPoint):
        # robin_stocks does not currently support getting top movers for crypto, so I need to set ones to watch manually
        self.cryptoWatchList = cryptoWatchList
        self.interval = interval
        self.span = span
        self.dataPoint = dataPoint

    def getTop100MarketMovers(self, limit=100):
        # get top 100 movers on Robinhood and pass them to a list
        tickerList = rs.markets.get_top_100(info='symbol')
        tickerList = tickerList[:limit]
        return tickerList

    # gets all cryptos (on watchlist and in portfolio) and combines them into one list

    def getCryptoList(self):
        cryptoList = self.cryptoWatchList
        cryptoPortfolioSymbols = self.getPortfolioCryptoSymbols()
        for x in cryptoPortfolioSymbols:
            if x not in cryptoList:
                cryptoList.append(x)
        return cryptoList

    def addCryptoToTickerList(self, tickerList):
        return tickerList.extend(self.getCryptoList())

    def getHistPrices(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            stockHistPrices = rs.crypto.get_crypto_historicals(tickerSymbol, interval=self.interval, span=self.span)
        else:
            stockHistPrices = rs.stocks.get_stock_historicals(tickerSymbol, interval=self.interval, span=self.span)
        return stockHistPrices

    def getCurrentPrice(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            return self.getCurrentCryptoPrice(tickerSymbol)
        stockHistPrices = self.getHistPrices(tickerSymbol)
        lastPrice = float(stockHistPrices[-1].get('close_price'))
        return lastPrice

    def getPriceChange(self, tickerSymbol):
        stockHistPrices = self.getHistPrices(tickerSymbol)
        priceChange = 0
        firstPrice = float(stockHistPrices[0].get(self.dataPoint))
        for i, x in enumerate(stockHistPrices[1:], start=1):
            priceChange = float(stockHistPrices[i].get(self.dataPoint)) - float(
                stockHistPrices[i - 1].get(self.dataPoint))
        return priceChange / firstPrice

    def getMultiplePriceChanges(self, tickerList):
        moverData = {}
        for x in tickerList:
            moverData[x] = self.getPriceChange(x)
        return moverData

    def getCurrentCryptoPrice(self, ticker):
        return float(rs.crypto.get_crypto_quote(ticker, info='mark_price'))

    def limitTopMovers(self, tickerList, limit=10, direction='up'):
        tickerPriceChangeDict = self.getMultiplePriceChanges(tickerList)
        sortedTickerDict = dict(reversed(sorted(tickerPriceChangeDict.items(), key=lambda item: item[1])))
        if direction == 'down':
            sortedTickerDict = dict(sorted(tickerPriceChangeDict.items(), key=lambda item: item[1]))
        elif direction != 'up':
            return "ERROR: Invalid parameter value"
        return list(sortedTickerDict.keys())[:limit]

    def combineTopMoversWithCrypto(self):
        topMovers = self.getTop100MarketMovers()
        topMovers.extend(self.getCryptoList())
        return topMovers

    def sortTopMovers(self, tickerList, positive=True):
        tickerPriceChangeDict = self.getMultiplePriceChanges(tickerList)
        singleSidedTickerDict = {}
        if positive:
            sortedTickerDict = dict(reversed(sorted(tickerPriceChangeDict.items(), key=lambda item: item[1])))
            for key, value in sortedTickerDict.items():
                if value > 0:
                    singleSidedTickerDict[key] = value
            return singleSidedTickerDict
        sortedTickerDict = dict((sorted(tickerPriceChangeDict.items(), key=lambda item: item[1])))
        for key, value in sortedTickerDict.items():
            if value < 0:
                singleSidedTickerDict[key] = value
        return singleSidedTickerDict

    def getPortfolioSymbols(self, includeCrypto=True):
        portfolioItems = rs.account.build_holdings()
        tickerSymbols = list(portfolioItems.keys())
        if includeCrypto:
            cryptoSymbolList = self.getPortfolioCryptoSymbols()
            for x in cryptoSymbolList:
                tickerSymbols.append(x)
        return tickerSymbols

    def getPortfolioCryptoSymbols(self):
        cryptoPortfolioItems = rs.crypto.get_crypto_positions()
        cryptPortfolioSymbolList = []
        for x in cryptoPortfolioItems:
            cryptoSymbol = (x.get('currency')).get('code')
            if cryptoSymbol != 'USD':
                cryptPortfolioSymbolList.append(cryptoSymbol)
        return cryptPortfolioSymbolList

    def getCryptoPortfolioEquity(self):
        cryptoTickerDict = {}
        cryptoPortfolioItems = rs.crypto.get_crypto_positions()
        for i, x in enumerate(cryptoPortfolioItems):
            code = (x.get('currency')).get('code')
            if code != 'USD':
                quantity = float((cryptoPortfolioItems[i].get('cost_bases')[0]).get('direct_quantity'))
                cryptoTickerDict[code] = quantity * self.getCurrentCryptoPrice(code)
        return cryptoTickerDict

    def getSingleCryptoEquity(self, tickerSymbol):
        cryptoPortfolioItems = rs.crypto.get_crypto_positions()
        for i, x in enumerate(cryptoPortfolioItems):
            code = (x.get('currency')).get('code')
            if code == tickerSymbol:
                quantity = float((cryptoPortfolioItems[i].get('cost_bases')[0]).get('direct_quantity'))
                return quantity * self.getCurrentCryptoPrice(code)

    def getPortfolioEquity(self, includeCrypto=True):
        tickerDict = {}
        portfolioItems = rs.account.build_holdings()
        tickerSymbols = self.getPortfolioSymbols(False)
        for i, x in enumerate(tickerSymbols):
            tickerDict[tickerSymbols[i]] = float((portfolioItems.get(x)).get('equity'))
        if includeCrypto:
            tickerDict.update(self.getCryptoPortfolioEquity())
        return tickerDict

    def getBuyingPower(self):
        return float(rs.profiles.load_account_profile(info='buying_power'))

    def getTotalInvested(self, includeCrypto=True):
        return sum(self.getPortfolioEquity(includeCrypto).values())

    def getTotalInRobinhood(self):
        return self.getBuyingPower() + self.getTotalInvested()
        self.getTotalInvested()

    def getPortfolioPriceChanges(self, includeCrypto=True):
        return self.getMultiplePriceChanges(self.getPortfolioSymbols(includeCrypto))

    def sortPricesChanges(self, priceDict, direction='asc'):
        if direction == 'desc':
            return dict(reversed(sorted(priceDict.items(), key=lambda item: item[1])))
        return dict(sorted(priceDict.items(), key=lambda item: item[1]))

    def get52WeekHigh(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            return float(max(rs.crypto.get_crypto_historicals(tickerSymbol, 'day', 'year', info='high_price')))
        return float(rs.stocks.get_fundamentals(tickerSymbol, info='high_52_weeks')[0])

    def getSymbolEquity(self, tickerSymbol):
        portfolioItems = rs.account.build_holdings()
        if tickerSymbol in self.getCryptoList():
            return self.getSingleCryptoEquity(tickerSymbol)
        return float((portfolioItems.get(tickerSymbol)).get('equity'))


class robExecutor(robRetriever):
    def __init__(self, cryptoWatchList, interval, span, dataPoint, sellYearThreshold, offloadYearThreshold,
                 buyYearThreshold, avoidYearThreshold, buyThreshold, sellThreshold, portfolioSellThreshold,
                 portfolioBuyThreshold, buyingPowerThreshold):
        super(robExecutor, self).__init__(cryptoWatchList, interval, span, dataPoint)
        self.sellYearThreshold = sellYearThreshold
        self.offloadYearThreshold = offloadYearThreshold
        self.buyYearThreshold = buyYearThreshold
        self.avoidYearThreshold = avoidYearThreshold
        self.buyThreshold = buyThreshold
        self.sellThreshold = sellThreshold
        self.portfolioSellThreshold = portfolioSellThreshold
        self.portfolioBuyThreshold = portfolioBuyThreshold
        self.interval = interval
        self.span = span
        self.cryptoWatchList = cryptoWatchList
        self.dataPoint = dataPoint
        self.buyingPowerThreshold = buyingPowerThreshold

    def sellPortfolio(self, includeCrypto=True, cryptoOnly=False):

        if cryptoOnly:
            portfolioDict = self.sortTopMovers(self.getPortfolioCryptoSymbols(), True).items()
        elif includeCrypto:
            portfolioDict = self.sortTopMovers(self.getPortfolioSymbols(), True).items()
        else:
            portfolioDict = self.sortTopMovers(self.getPortfolioSymbols(False), True).items()
        resultList = []
        for key, value in portfolioDict:
            """
            sell stock if the price change is above the sell threshold and current price is not too close to the 52 week
            high, or if the stock has dipped a certain amount as a percentage of its 52 week high
            """

            if (value > self.sellThreshold and self.getCurrentPrice(key) / self.get52WeekHigh(
                    key) < self.offloadYearThreshold) or self.getCurrentPrice(key) / self.get52WeekHigh(
                key) < self.offloadYearThreshold:
                resultList.append('Sell ', key, ' Result: ', self.sell(key))
        if resultList == []:
            return "No portfolio items meet criteria for sale."
        else:
            return resultList

    def sell(self, tickerSymbol):
        """
        sell stock up to x% of total portfolio.
        """
        sellAmount = self.getSymbolEquity(tickerSymbol)
        if sellAmount / self.getTotalInRobinhood() > self.portfolioSellThreshold:
            sellAmount = self.portfolioSellThreshold * self.getTotalInRobinhood()

        if tickerSymbol in self.getCryptoList():
            result = rs.orders.order_sell_crypto_by_price(tickerSymbol, sellAmount)
            while result.get('non_field_errors') == 'Insufficient holdings.':
                sellAmount = sellAmount * .95
                result = rs.orders.order_sell_crypto_by_price(tickerSymbol, sellAmount)
        if tickerSymbol not in self.getCryptoList():
            result = rs.orders.order_sell_fractional_by_price(tickerSymbol, sellAmount)
            while result.get('detail') == 'Not enough shares to sell.':
                sellAmount = sellAmount * .95
                result = rs.orders.order_sell_fractional_by_price(tickerSymbol, sellAmount)
        return result

    def buyFromMarket(self, includeCrypto=True, onlyCrypto=False):
        buyAmount = self.getBuyingPower()
        if buyAmount / self.getTotalInRobinhood() < self.buyingPowerThreshold:
            return "No stocks purchased; not enough buying power."
        if onlyCrypto:
            marketDict = self.sortTopMovers(self.getCryptoList(), False).items()
        elif includeCrypto:
            marketDict = self.sortTopMovers(self.combineTopMoversWithCrypto(), False).items()
        else:
            marketDict = self.sortTopMovers(self.getTop100MarketMovers(), False).items()
        resultList = []
        for key, value in marketDict:
            """
            buy stock if the price change is below the buy threshold and current price is not too close to the 52 week
            high and if the stock is not under a certain amount as a percentage of its 52 week high
            """
            if value < self.buyThreshold and self.avoidYearThreshold < self.getCurrentPrice(key) / self.get52WeekHigh(
                    key) < self.buyYearThreshold:
                resultList.append('Buy ', key, ' Result: ', self.buy(key))
        if resultList == []:
            return "No stocks meet criteria for purchase."
        else:
            return resultList

    def buy(self, tickerSymbol):
        buyAmount = self.getBuyingPower()
        if buyAmount / self.getTotalInRobinhood() < self.buyingPowerThreshold:
            return "Not enough buying power"
        if buyAmount / self.getTotalInRobinhood() > self.portfolioBuyThreshold:
            buyAmount = self.portfolioBuyThreshold * self.getTotalInRobinhood()
        if buyAmount < 1:
            return "Fraction too small to purchase"
        if tickerSymbol in self.getCryptoList():
            result = rs.orders.order_buy_crypto_by_price(tickerSymbol, buyAmount)
            while result.get('non_field_errors') == 'Insufficient holdings..':
                buyAmount = buyAmount * .95
                if buyAmount < 1:
                    "Fraction too small to purchase"
                result = rs.orders.order_buy_crypto_by_price(tickerSymbol, buyAmount)
        if tickerSymbol not in self.getCryptoList():
            result = rs.orders.order_buy_fractional_by_price(tickerSymbol, buyAmount)
            while 'You can only purchase' in result.get('detail'):
                buyAmount = buyAmount * .95
                if buyAmount < 1:
                    "Fraction too small to purchase"
                result = rs.orders.order_sell_fractional_by_price(tickerSymbol, buyAmount)
        return result
