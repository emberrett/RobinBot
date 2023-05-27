import example_config
from robin_bot import RobinBot, RobinCryptoBot
robin_bot = RobinCryptoBot(**example_config.config)
robin_bot.login()
print(robin_bot.get_52_week_high('AAPL'))
robin_bot.logout()
