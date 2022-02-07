import robin_stocks.robinhood as rs
import os


class robLogin:
    def login(self):
        robin_user = os.environ.get("robinhood_username")
        robin_pass = os.environ.get("robinhood_password")
        rs.login(username=robin_user, password=robin_pass, by_sms=True)

    def logout(self):
        rs.logout()


class robRetriever:
    def __init__(self, cryptoWatchList, interval, span, dataPoint):
        # robin_stocks does not currently support getting top movers for crypto, so I need to set ones to watch manually
        self.cryptoWatchList = cryptoWatchList
        self.interval = interval
        self.span = span
        self.dataPoint = dataPoint

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

    def getCryptoList(self):
        cryptoList = self.cryptoWatchList
        cryptoPortfolioSymbols = self.getPortfolioCryptoSymbols()
        for x in cryptoPortfolioSymbols:
            if x not in cryptoList:
                cryptoList.append(x)
        return cryptoList

    def getAverageCost(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            return self.getCryptoAverageCost(tickerSymbol)
        else:
            return float((rs.account.build_holdings().get(tickerSymbol)).get('average_buy_price'))

    def getCryptoAverageCost(self, tickerSymbol):
        cryptoPortfolioItems = rs.crypto.get_crypto_positions()
        for i, x in enumerate(cryptoPortfolioItems):
            code = (x.get('currency')).get('code')
            if code == tickerSymbol:
                costBasis = float((cryptoPortfolioItems[i].get('cost_bases')[0]).get('direct_cost_basis'))
                quantity = float((cryptoPortfolioItems[i].get('cost_bases')[0]).get('direct_quantity'))
                return costBasis / quantity

    def getHistPrices(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            stockHistPrices = rs.crypto.get_crypto_historicals(tickerSymbol, interval=self.interval, span=self.span)
        else:
            stockHistPrices = rs.stocks.get_stock_historicals(tickerSymbol, interval=self.interval, span=self.span)
        return stockHistPrices

    def getCurrentPrice(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            return self.getCurrentCryptoPrice(tickerSymbol)
        return float(rs.markets.get_stock_quote_by_symbol(tickerSymbol).get('last_trade_price'))

    def getCurrentCryptoPrice(self, ticker):
        return float(rs.crypto.get_crypto_quote(ticker, info='mark_price'))

    def getPriceChange(self, tickerSymbol):
        stockHistPrices = self.getHistPrices(tickerSymbol)
        firstPrice = float(stockHistPrices[0].get(self.dataPoint))
        currentPrice = self.getCurrentPrice(tickerSymbol)
        return (currentPrice - firstPrice) / firstPrice

    def getMultiplePriceChanges(self, tickerList):
        moverData = {}
        for x in tickerList:
            moverData[x] = self.getPriceChange(x)
        return moverData

    def getTop100MarketMovers(self, limit=100):
        # get top 100 movers on Robinhood and pass them to a list
        tickerList = rs.markets.get_top_100(info='symbol')
        tickerList = tickerList[:limit]
        return tickerList

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

    def getSymbolEquity(self, tickerSymbol):
        portfolioItems = rs.account.build_holdings()
        if tickerSymbol in self.getCryptoList():
            return self.getSingleCryptoEquity(tickerSymbol)
        return float((portfolioItems.get(tickerSymbol)).get('equity'))

    def getCryptoPortfolioEquity(self):
        cryptoTickerDict = {}
        cryptoPortfolioItems = rs.crypto.get_crypto_positions()
        for i, x in enumerate(cryptoPortfolioItems):
            code = (x.get('currency')).get('code')
            if code != 'USD':
                cryptoTickerDict[code] = float(self.getSingleCryptoEquity(code))
        return cryptoTickerDict

    def getTotalCryptoEquity(self):
        return sum(self.getCryptoPortfolioEquity().values())

    def getTotalEquity(self, includeCrypto=True):
        stockPortfolioDict = rs.account.build_holdings()
        portfolioEquity = 0
        for key, value in stockPortfolioDict.items():
            portfolioEquity += (float(value.get('equity')))
        if includeCrypto:
            return portfolioEquity + self.getTotalCryptoEquity()
        return portfolioEquity

    def getSingleCryptoEquity(self, tickerSymbol):
        cryptoPortfolioItems = rs.crypto.get_crypto_positions()
        for i, x in enumerate(cryptoPortfolioItems):
            code = (x.get('currency')).get('code')
            if code == tickerSymbol:
                quantity = float((cryptoPortfolioItems[i].get('cost_bases')[0]).get('direct_quantity'))
                return quantity * self.getCurrentCryptoPrice(code)

    def getShares(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            cryptoPortfolioItems = rs.crypto.get_crypto_positions()
            for i, x in enumerate(cryptoPortfolioItems):
                code = (x.get('currency')).get('code')
                if code == tickerSymbol:
                    quantity = float((cryptoPortfolioItems[i].get('cost_bases')[0]).get('direct_quantity'))
                    return quantity
        else:
            portfolioItems = rs.account.build_holdings()
            if tickerSymbol in self.getCryptoList():
                return self.getCryptoShares(tickerSymbol)
            return float((portfolioItems.get(tickerSymbol)).get('quantity'))

    def getBuyingPower(self):
        return float(rs.profiles.load_account_profile(info='buying_power'))

    def getTotalInvested(self, includeCrypto=True):
        return self.getBuyingPower() + self.getTotalEquity(includeCrypto=includeCrypto)

    def getTotalInRobinhood(self):
        return self.getBuyingPower() + self.getTotalInvested()
        self.getTotalInvested()

    def get52WeekHigh(self, tickerSymbol):
        if tickerSymbol in self.getCryptoList():
            return float(max(rs.crypto.get_crypto_historicals(tickerSymbol, 'day', 'year', info='high_price')))
        return float(rs.stocks.get_fundamentals(tickerSymbol, info='high_52_weeks')[0])


class robExecutor(robRetriever):
    def __init__(self, cryptoWatchList, interval, span, dataPoint, sellYearThreshold,
                 sellDollarLimit,
                 buyYearThreshold, avoidYearThreshold, buyThreshold, portfolioSellThreshold,
                 portfolioBuyThreshold, buyingPowerLimit, buyDollarLimit, profitThreshold):
        super(robExecutor, self).__init__(cryptoWatchList, interval, span, dataPoint)
        self.sellYearThreshold = sellYearThreshold
        self.sellDollarLimit = sellDollarLimit
        self.buyYearThreshold = buyYearThreshold
        self.avoidYearThreshold = avoidYearThreshold
        self.buyThreshold = buyThreshold
        self.portfolioSellThreshold = portfolioSellThreshold
        self.portfolioBuyThreshold = portfolioBuyThreshold
        self.interval = interval
        self.span = span
        self.cryptoWatchList = cryptoWatchList
        self.dataPoint = dataPoint
        self.buyingPowerLimit = buyingPowerLimit
        self.buyDollarLimit = buyDollarLimit
        self.profitThreshold = profitThreshold

    def sellPortfolio(self, includeCrypto=True, onlyCrypto=False, printResults=False, sellLimit=False,
                      sellFractional=False):
        # get list of portfolio tickers
        if onlyCrypto:
            tickerList = self.getPortfolioCryptoSymbols()
        elif includeCrypto:
            tickerList = self.getPortfolioSymbols()
        else:
            tickerList = self.getPortfolioSymbols(includeCrypto=False)
        index = 1
        resultList = []
        totalInRobinhood = self.getTotalInRobinhood()
        for ticker in tickerList:
            if sellLimit is not False:
                if index > sellLimit:
                    resultItem = "Max number of stock sales reached."
                    resultList.append(resultItem)
                    if printResults:
                        print(resultItem)
                    return resultList
            index += 1
            result = str(self.sellWithConditions(ticker, totalInvested=totalInRobinhood, sellFractional=sellFractional))
            resultItem = str('Sell ' + ticker + ' Result: ' + result)
            resultList.append(resultItem)
            if printResults:
                print(resultItem)
        return resultList

    def sellWithConditions(self, tickerSymbol, totalInvested, sellFractional=False):
        currentShares = self.getShares(tickerSymbol)
        if currentShares == 0:
            return "No shares available for sale."
        averageCost = self.getAverageCost(tickerSymbol)
        currentPrice = self.getCurrentPrice(tickerSymbol)
        # check to see if profit meets threshold
        profit = (currentPrice - averageCost) / averageCost
        if profit < self.profitThreshold:
            return "Profit of sale does not meet profit threshold. (" + "{:.2%}".format(profit) + ")"
        yearHigh = self.get52WeekHigh(tickerSymbol)
        # check that the price isn't too close to the 52-week high
        if currentPrice / yearHigh > self.sellYearThreshold:
            return "Proximity to 52 week high exceeds threshold. Price: " + str(
                currentPrice) + " 52-week high: " + yearHigh
        sellAmount = self.getSymbolEquity(tickerSymbol)
        currentEquity = sellAmount

        # sell all shares of stock if sellFractional is false
        if sellAmount == 0 or sellFractional is False:
            return self.sell(currentShares, tickerSymbol, True)

        # if sale account for more than certain % of portfolio, lower the number to the max % of portfolio
        if sellAmount / totalInvested > self.portfolioSellThreshold:
            sellAmount = self.portfolioSellThreshold * totalInvested

        # if sale amount < dollar limit, sell as shares as opposed to price to avoid $1 sale restriction
        if sellAmount < self.sellDollarLimit:
            sellAmount = sellAmount / currentPrice
            if sellAmount > currentShares:
                sellAmount = currentShares
            return self.sell(sellAmount, tickerSymbol, True)
        # if equity - sale amount < the dollar limit, sell all shares
        if abs(currentEquity - sellAmount) < self.sellDollarLimit:
            return self.sell(currentShares, tickerSymbol, True)
        return self.sell(sellAmount, tickerSymbol)

    def sell(self, sellAmount, tickerSymbol, shares=False):
        if tickerSymbol in self.getCryptoList():
            if shares:
                result = rs.orders.order_sell_crypto_by_quantity(tickerSymbol, round(sellAmount, 8))
                return result
            result = rs.orders.order_sell_crypto_by_price(tickerSymbol, sellAmount)
            if result.get('non_field_errors') == ['Insufficient holdings.']:
                totalShares = self.getCryptoShares(tickerSymbol)
                result = rs.orders.order_sell_crypto_by_quantity(tickerSymbol, totalShares)
                return result
            return result

        if tickerSymbol not in self.getCryptoList():
            if shares:
                result = rs.orders.order_sell_fractional_by_quantity(tickerSymbol, round(sellAmount, 6))
                return result
            result = rs.orders.order_sell_fractional_by_price(tickerSymbol, sellAmount)
            if result.get('detail') == 'Not enough shares to sell.':
                totalShares = self.getShares(tickerSymbol)
                result = rs.orders.order_sell_fractional_by_quantity(tickerSymbol, totalShares)
                return result
        return result

    def buyFromMarket(self, includeCrypto=True, onlyCrypto=False, printResults=False, buyLimit=False,
                      excludePortfolioItems=True):
        robinHoodTotal = self.getTotalInRobinhood()
        portfolioSymbols = []
        if excludePortfolioItems:
            portfolioSymbols = self.getPortfolioSymbols(includeCrypto=includeCrypto)
        if onlyCrypto:
            marketDict = self.sortTopMovers(self.getCryptoList(), False).items()
        elif includeCrypto:
            marketDict = self.sortTopMovers(self.combineTopMoversWithCrypto(), False).items()
        else:
            marketDict = self.sortTopMovers(self.getTop100MarketMovers(), False).items()
        resultList = []
        index = 1
        if not marketDict:
            return "No negative change for given symbols."
        for key, value in marketDict:
            """
            buy stock if the price change is below the buy threshold and current price is not too close to the 52 week
            high and if the stock is not under a certain amount as a percentage of its 52 week high
            """
            if buyLimit is not False:
                if index > buyLimit:
                    resultItem = "Max number of stock purchases reached. (" + str(buyLimit) + ")"
                    resultList.append(resultItem)
                    if printResults:
                        print(resultItem)
                    return resultList
            result = str(self.buyWithConditions(key, robinHoodTotal, portfolioSymbols=portfolioSymbols))
            resultItem = str('Buy ' + key + ' Result: ' + result)
            resultList.append(resultItem)
            index += 1
            if printResults:
                print(resultItem)

        return resultList

    # change so that we don't buy tickers we already have in our portfolio
    def buyWithConditions(self, tickerSymbol, totalInvested, portfolioSymbols=[]):
        if tickerSymbol in portfolioSymbols:
            return "Symbol already in portfolio."
        buyingPower = self.getBuyingPower()
        buyingPowerLimit = self.buyingPowerLimit
        portFolioBuyThreshold = self.portfolioBuyThreshold
        buyAmount = buyingPower * buyingPowerLimit
        priceChange = self.getPriceChange(tickerSymbol)
        currentPrice = self.getCurrentPrice(tickerSymbol)
        yearHigh = self.get52WeekHigh(tickerSymbol)
        if buyingPower < self.buyDollarLimit:
            return "Buying power less than dollar limit. (" + str(buyingPower) + ")"
        # check if purchase takes up too much of portfolio
        if buyAmount / totalInvested > portFolioBuyThreshold:
            buyAmount = portFolioBuyThreshold * totalInvested
        # check if buy amount is greater than buying power limit
        if buyAmount / buyingPower > buyingPowerLimit:
            buyAmount = buyingPower * buyingPowerLimit
        # if buy amount is less than dollar limit, set buy amount to dollar
        if buyAmount < self.buyDollarLimit:
            buyAmount = self.buyDollarLimit
        if priceChange < self.buyThreshold:
            if currentPrice / yearHigh > self.avoidYearThreshold:
                if currentPrice / yearHigh < self.buyYearThreshold:
                    return self.buy(tickerSymbol=tickerSymbol, buyAmount=buyAmount)
                else:
                    return "Price too close to 52-week high threshold. Price: " + str(
                        currentPrice) + " 52-week high: " + str(yearHigh)
            else:
                return "Price too far from 52-week high threshold. Price: " + str(
                    currentPrice) + " 52-week high: " + str(yearHigh)
        else:
            return "Price decrease lower than buy threshold. (" + "{:.2%}".format(priceChange) + ")"

    def buy(self, tickerSymbol, buyAmount):
        if tickerSymbol in self.getCryptoList():
            result = rs.orders.order_buy_crypto_by_price(tickerSymbol, buyAmount)
            while result.get('non_field_errors') == ['Insufficient holdings.']:
                buyAmount = buyAmount * .90
                if buyAmount < self.buyDollarLimit:
                    return "Fraction too small to purchase (" + str(buyAmount) + ")"
                result = rs.orders.order_buy_crypto_by_price(tickerSymbol, buyAmount)
        if tickerSymbol not in self.getCryptoList():
            result = rs.orders.order_buy_fractional_by_price(tickerSymbol, buyAmount)
            if result.get('detail') is not None:
                while 'You can only purchase' in result.get(
                        'detail'):
                    buyAmount = buyAmount * .90
                    if buyAmount < self.buyDollarLimit:
                        return "Fraction too small to purchase (" + str(buyAmount) + ")"
                result = rs.orders.order_sell_fractional_by_price(tickerSymbol, buyAmount)
        return result
