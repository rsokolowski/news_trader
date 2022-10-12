import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


from automatic_trader import AutomaticTrader
from exchange_client_mock import ExchangeClientMock
from exchange_client import MARKET_TYPE
from clock import Clock


mock = ExchangeClientMock()
mock.balance_per_market_type = {
    MARKET_TYPE.SPOT: 1000,
    MARKET_TYPE.MARGIN: 2000,
    MARKET_TYPE.FUTURES: 3000
}
mock.market_type = MARKET_TYPE.FUTURES
mock.currency = "ETH"
mock.max_leverage = 10
mock.fill_buy = False
mock.fill_sell_attempts = 3
mock.prices = [
    [0, 100],
    [1, 101],
    [2, 102],
    [28, 100],
    [45, 100],
    [50, 99]
]
# mock.prices = [
#     [0, 100],
#     [1, 101],
#     [2, 98],
#     [4, 97],
#     [45, 100],
#     [50, 99]
# ]
# mock.prices = [
#     [0, 100],
#     [1, 101],
#     [2, 102],
#     [40, 105],
#     [45, 100],
#     [50, 99]
# ]
mock.run()

trader = AutomaticTrader(Clock(), mock, "ETH")
trader.up_and_to_the_right()

