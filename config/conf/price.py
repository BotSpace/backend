# type: ignore
from config.env import env


RAM_PRICE = env.int("RAM_PRICE", 0)
CPU_PRICE = env.int("CPU_PRICE", 0)
NET_TX_PRICE = env.int("NET_TX_PRICE", 0)
NET_RX_PRICE = env.int("NET_RX_PRICE", 0)
STORAGE_PRICE = env.int("STORAGE_PRICE", 0)
