# type: ignore
from config.env import env


RAM_PRICE = env.int("RAM_PRICE", 1000)
CPU_PRICE = env.int("CPU_PRICE", 1000)
NET_TX_PRICE = env.int("NET_TX_PRICE", 1000)
NET_RX_PRICE = env.int("NET_RX_PRICE", 1000)
STORAGE_PRICE = env.int("STORAGE_PRICE", 1000)
