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

    def getPortfolioPriceChanges(self, includeCrypto=True):
        return self.getMultiplePriceChanges(self.getPortfolioSymbols(includeCrypto))

    def sortPricesChanges(self, priceDict, direction='asc'):
        if direction == 'desc':
            return dict(reversed(sorted(priceDict.items(), key=lambda item: item[1])))
        return dict(sorted(priceDict.items(), key=lambda item: item[1]))

    def getTop100MarketMovers(self, limit=100):
        # get top 100 movers on Robinhood and pass them to a list
        tickerList = rs.markets.get_top_100(info='symbol')
        tickerList = tickerList[:limit]
        return tickerList

    def limitTopMovers(self, tickerList, limit=10, direction='up'):
        tickerPriceChangeDict = self.getMultiplePriceChanges(tickerList)
        sortedTickerDict = dict(reversed(sorted(tickerPriceChangeDict.items(), key=lambda item: item[1])))
        if direction == 'down':
            sortedTickerDict = dict(sorted(tickerPriceChangeDict.items(), key=lambda item: item[1]))
        elif direction != 'up':
            return "ERROR: Invalid parameter value"
        return list(sortedTickerDict.keys())[:limit]

    def getTopPortfolioMovers(self, positive=True, includeCrypto=True, onlyCrypto=False):
        costDifferenceDict = {}
        singleSidedCostDifferenceDict = {}
        symbolList = self.getPortfolioSymbols(includeCrypto=includeCrypto)
        if onlyCrypto:
            symbolList = self.getPortfolioCryptoSymbols()
        for x in symbolList:
            averageCost = self.getAverageCost(x)
            currentPrice = self.getCurrentPrice(x)
            costDifferenceDict[x] = (currentPrice - averageCost) / averageCost
        costDifferenceDict = dict(reversed(sorted(costDifferenceDict.items(), key=lambda item: item[1])))
        if not positive:
            costDifferenceDict = dict(sorted(costDifferenceDict.items(), key=lambda item: item[1]))

        if positive:
            for key, value in costDifferenceDict.items():
                if value > 0:
                    singleSidedCostDifferenceDict[key] = value
        else:
            for key, value in costDifferenceDict.items():
                if value < 0:
                    singleSidedCostDifferenceDict[key] = value

        return singleSidedCostDifferenceDict

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

    def getPortfolioEquity(self, includeCrypto=True):
        tickerDict = {}
        tickerSymbols = self.getPortfolioSymbols(includeCrypto)
        for i, x in enumerate(tickerSymbols):
            tickerDict[tickerSymbols[i]] = self.getSymbolEquity(x)
        return tickerDict

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
    def __init__(self, cryptoWatchList, interval, span, dataPoint, sellYearThreshold, offloadYearThreshold,
                 sellDollarLimit,
                 buyYearThreshold, avoidYearThreshold, buyThreshold, portfolioSellThreshold,
                 portfolioBuyThreshold, buyingPowerLimit, buyDollarLimit, profitThreshold):
        super(robExecutor, self).__init__(cryptoWatchList, interval, span, dataPoint)
        self.sellYearThreshold = sellYearThreshold
        self.offloadYearThreshold = offloadYearThreshold
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

    def sellPortfolio(self, includeCrypto=True, onlyCrypto=False, printResults=False, sellLimit=False):
        # need to just change to check to sell all stocks in portfolio, will do this in the future.
        portfolioDict = self.getTopPortfolioMovers(onlyCrypto=onlyCrypto, includeCrypto=includeCrypto).items()
        if not portfolioDict:
            return "No profit to be made from given portfolio holdings."
        resultList = []
        index = 1
        totalInRobinhood = self.getTotalInRobinhood()
        for key, value in portfolioDict:
            """
            sell stock if the price change is above the sell threshold and current price is not too close to the 52 week
            high, or if the stock has dipped a certain amount as a percentage of its 52 week high
            """
            if sellLimit is not False:
                if index > sellLimit:
                    resultItem = "Max number of stock sales reached."
                    resultList.append(resultItem)
                    if printResults:
                        print(resultItem)
                    return resultList
            index += 1
            result = str(self.sellWithConditions(key, totalInvested=totalInRobinhood))
            resultItem = str('Sell ' + key + ' Result: ' + result)
            resultList.append(resultItem)
            if printResults:
                print(resultItem)
        return resultList

    def sellWithConditions(self, tickerSymbol, totalInvested):
        """
        sell stock up to x% of total portfolio.
        """
        yearHigh = self.get52WeekHigh(tickerSymbol)
        averageCost = self.getAverageCost(tickerSymbol)
        currentPrice = self.getCurrentPrice(tickerSymbol)
        sellAmount = self.getSymbolEquity(tickerSymbol)
        currentEquity = sellAmount
        currentShares = self.getShares(tickerSymbol)

        # if sale account for more than certain % of portfolio, lower the number to the max % of portfolio
        if sellAmount / totalInvested > self.portfolioSellThreshold:
            sellAmount = self.portfolioSellThreshold * totalInvested
        # if current price is far enough away from 52-week high, offload the shares
        #NEED TO ADD LOGIC FOR NOT SELLING IF PROFIT IS POSITIVE, MAYBE DON'T NEED THIS WITH AVOID THRESHOLD
        if currentPrice / yearHigh < self.offloadYearThreshold:
            return self.sell(sellAmount, tickerSymbol)
        # check that the price isn't too close to the 52-week high
        if currentPrice / yearHigh < self.sellYearThreshold:
            # check that the sale meets the profit threshold
            if (currentPrice - averageCost) / averageCost > self.profitThreshold:
                # equity only stores two decimal places, need to sell all shares if the sale amount is zero
                if sellAmount == 0:
                    return self.sell(currentShares, tickerSymbol, True)
                # if sale amount < dollar limit, sell as shares as opposed to price to avoid $1 sale restriction
                if sellAmount < self.sellDollarLimit:
                    sellAmount = sellAmount / currentPrice
                    if sellAmount > currentShares:
                        sellAmount = currentShares
                    return self.sell(sellAmount, tickerSymbol, True)
                # if equity - sale amount < the dollar limit, sell all shares
                if currentEquity - sellAmount < self.sellDollarLimit:
                    return self.sell(currentShares, tickerSymbol, True)
                return self.sell(sellAmount, tickerSymbol)
            else:
                return "Profit of sale does not meet profit threshold."
        else:
            return "Proximity to 52 week high exceeds threshold."

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

    def buyFromMarket(self, includeCrypto=True, onlyCrypto=False, printResults=False, buyLimit=False):
        robinHoodTotal = self.getTotalInRobinhood()

        if onlyCrypto:
            marketDict = self.sortTopMovers(self.getCryptoList(), False).items()
        elif includeCrypto:
            marketDict = self.sortTopMovers(self.combineTopMoversWithCrypto(), False).items()
        else:
            marketDict = self.sortTopMovers(self.getTop100MarketMovers(), False).items()
        resultList = []
        index = 1
        if not marketDict:
            return "No negative change for provided portfolio symbols."
        for key, value in marketDict:
            """
            buy stock if the price change is below the buy threshold and current price is not too close to the 52 week
            high and if the stock is not under a certain amount as a percentage of its 52 week high
            """
            if buyLimit is not False:
                if index > buyLimit:
                    resultItem = "Max number of stock purchases reached."
                    resultList.append(resultItem)
                    if printResults:
                        print(resultItem)
                    return resultList
            result = str(self.buyWithConditions(key, robinHoodTotal))
            resultItem = str('Buy ' + key + ' Result: ' + result)
            resultList.append(resultItem)
            index += 1
            if printResults:
                print(resultItem)

        return resultList

    def buyWithConditions(self, tickerSymbol, totalInvested):
        buyingPower = self.getBuyingPower()
        buyingPowerLimit = self.buyingPowerLimit
        portFolioBuyThreshold = self.portfolioBuyThreshold
        buyAmount = buyingPower * buyingPowerLimit
        priceChange = self.getPriceChange(tickerSymbol)
        currentPrice = self.getCurrentPrice(tickerSymbol)
        yearHigh = self.get52WeekHigh(tickerSymbol)
        if buyAmount == 0:
            return "No buying power."
        if buyAmount < self.buyDollarLimit:
            return "Fraction too small to purchase"
        if buyAmount / totalInvested > portFolioBuyThreshold:
            buyAmount = portFolioBuyThreshold * totalInvested
        if buyAmount / buyingPower > buyingPowerLimit:
            buyAmount = buyingPower * buyingPowerLimit

        if priceChange < self.buyThreshold:
            if currentPrice / yearHigh > self.avoidYearThreshold:
                if currentPrice / yearHigh < self.buyYearThreshold:
                    return self.buy(tickerSymbol=tickerSymbol, buyAmount=buyAmount)
                else:
                    return "Too close to 52-week high threshold."
            else:
                return "Too far from 52-week high threshold."
        else:
            return "Price decrease lower than buy threshold."

    def buy(self, tickerSymbol, buyAmount):
        if tickerSymbol in self.getCryptoList():
            result = rs.orders.order_buy_crypto_by_price(tickerSymbol, buyAmount)
            while result.get('non_field_errors') == ['Insufficient holdings.']:
                buyAmount = buyAmount * .95
                if buyAmount < self.buyDollarLimit:
                    return "Fraction too small to purchase"
                result = rs.orders.order_buy_crypto_by_price(tickerSymbol, buyAmount)
        if tickerSymbol not in self.getCryptoList():
            result = rs.orders.order_buy_fractional_by_price(tickerSymbol, buyAmount)
            if result.get('detail') is not None:
                while 'You can only purchase' in result.get(
                        'detail'):
                    buyAmount = buyAmount * .95
                    if buyAmount < self.buyDollarLimit:
                        return "Fraction too small to purchase"
                result = rs.orders.order_sell_fractional_by_price(tickerSymbol, buyAmount)
        return result
