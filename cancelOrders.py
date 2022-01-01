from classes import robLogin
import robin_stocks.robinhood as rs

rl = robLogin()
rl.login()
rs.orders.cancel_all_stock_orders()
rl.logout()
