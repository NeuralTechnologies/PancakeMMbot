from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from app_logger import config
import app_logger
from database import DBManager
logger = app_logger.get_logger(__name__)
web3 = Web3(Web3.HTTPProvider(config['SETTINGS']['bsc_node_http']))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

with open('../../PancakeMMbot-data/abi/PancakeRouterV3.json') as f:
    PANCAKE_ROUTER_V3_ABI = json.load(f)
with open('../../PancakeMMbot-data/abi/token.json') as f:
    TOKEN_ABI = json.load(f)
with open('../../PancakeMMbot-data/abi/ubx.json') as f:
    UBX_ABI = json.load(f)
PANCAKE_ROUTER_ADDRESS_V3 = web3.to_checksum_address('0x13f4EA83D0bd40E75C8222255bc855a974568Dd4')
PANCAKE_ROUTER_CONTRACT_V3 = web3.eth.contract(address=PANCAKE_ROUTER_ADDRESS_V3, abi=PANCAKE_ROUTER_V3_ABI)

WBNB_ADDRESS = web3.to_checksum_address('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c')
WBNB_DECIMAL = 18

UBX_TOKEN = web3.to_checksum_address('0xcde131f756176967b695c6090885d387f1337456')
UBX_DECIMAL = 0
UBX_CONTRACT = web3.eth.contract(address=UBX_TOKEN, abi=UBX_ABI)

USDT_ADDRESS = web3.to_checksum_address('0x55d398326f99059fF775485246999027B3197955')
USDT_DECIMAL = 18
USDT_CONTRACT = web3.eth.contract(address=USDT_ADDRESS, abi=TOKEN_ABI)
db_manager = DBManager()
db_manager.initialize()

class HOLDER:
    def __init__(self, address, private_key):
        self.address = address
        self.private_key = private_key