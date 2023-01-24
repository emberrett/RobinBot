from robin_bot import RobLogin
import robin_stocks.robinhood as rs

rl = RobLogin()
rl.login()
rs.orders.cancel_all_stock_orders()
rl.logout()
