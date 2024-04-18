from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import schedule
from app_logger import config
from datetime import datetime, timezone, timedelta
from database import DBManager
from sqlalchemy.sql import func
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import random

db_manager = DBManager()
db_manager.initialize()

def get_data_from_graph(subgraph, graphql_query):
    transport = AIOHTTPTransport(url=subgraph)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query = gql(graphql_query)
    return client.execute(query)['swaps']


def get_data_every_minute():
    try:
        result = get_data_from_graph(config['SETTINGS']['graphql_url'], config['SETTINGS']['graphql_query'])
        db_session = db_manager.Session()
        max_datetime = db_session.query(func.max(db_manager.Base.classes.base_volume_minutes.timestamp)).scalar()
        volume0 = 0
        volume1 = 0
        print(max_datetime)
        print(max_datetime + 60)
        for row in result:
            if max_datetime <= int(row['timestamp']) < (max_datetime + 60):
                print(int(row['timestamp']))
                print(float(row['amount0']))
                print(float(row['amount1']))
                # if float(row['amount0']) > 0:
                volume0 += abs(float(row['amount0']))
                # if float(row['amount1']) > 0:
                volume1 += abs(float(row['amount1']))
        bvm = db_manager.Base.classes.base_volume_minutes()
        bvm.pool_id = 1
        bvm.datetime = datetime.fromtimestamp((max_datetime + 60))
        bvm.token0 = result[0]['token0']['symbol']
        bvm.token1 = result[0]['token1']['symbol']
        bvm.amount0 = volume0
        bvm.amount1 = volume1
        bvm.timestamp = (max_datetime + 60)
        db_session.add(bvm)
        db_session.commit()
        db_session.close()
    except Exception as e:
        print(e)


# get_data_every_minute()
# schedule.every().minute.at(":00").do(get_data_every_minute)
# while True:
#    schedule.run_pending()
#    time.sleep(1)


web3 = Web3(Web3.HTTPProvider(config['SETTINGS']['bsc_node_http']))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

with open('../../PancakeMMbot-data/abi/PancakeRouterV3.json') as f:
    PANCAKE_ROUTER_V3_ABI = json.load(f)

with open('../../PancakeMMbot-data/abi/token.json') as f:
    TOKEN_ABI = json.load(f)

PANCAKE_ROUTER_ADDRESS_V3 = web3.to_checksum_address('0x13f4EA83D0bd40E75C8222255bc855a974568Dd4')
PANCAKE_ROUTER_CONTRACT_V3 = web3.eth.contract(address=PANCAKE_ROUTER_ADDRESS_V3, abi=PANCAKE_ROUTER_V3_ABI)

WBNB_ADDRESS = web3.to_checksum_address('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c')
WBNB_DECIMAL = 18

router = PANCAKE_ROUTER_CONTRACT_V3

UBIX_TOKEN = web3.to_checksum_address('0xcde131f756176967b695c6090885d387f1337456')
UBIX_DECIMAL = 0
token_contract = web3.eth.contract(address=UBIX_TOKEN, abi=TOKEN_ABI)

victim_address = '0x1913cfb8AC8cf3ce346E1dE2C04FE8413f176672'
victim_private = 'f5445cea6ca210c617e81bb4cf105347e870b0ecc9ed361bf471b93189e6d476'
USDT_ADDRESS = web3.to_checksum_address('0x55d398326f99059fF775485246999027B3197955')
USDT_DECIMAL = 18


class HOLDER:
    def __init__(self, address, private_key):
        self.address = address
        self.private_key = private_key


def trade(side, amount, holder):
    if side == "buy":
        payload = (USDT_ADDRESS, UBIX_TOKEN, int(config['SETTINGS']['fee']), holder.address,
                   int(amount * 10 ** USDT_DECIMAL), 0, 0)
    else:
        amount = token_contract.functions.balanceOf(victim_address).call()
        payload = (UBIX_TOKEN, USDT_ADDRESS, int(config['SETTINGS']['fee']), holder.address,
                   int(amount * 10 ** UBIX_DECIMAL), 0, 0)
    nonce = web3.eth.get_transaction_count(holder.address)
    tx_exactInputSingle = router.functions.exactInputSingle(payload).build_transaction({
        'from': holder.address,
        'value': 0,
        'gasPrice': web3.to_wei(1, 'gwei'),
        'gas': int(config['SETTINGS']['gas_max']),
        'nonce': 1
    })

    tx_multicall = router.functions.multicall(
        int(time.time() + 10000),
        [tx_exactInputSingle['data']]
    ).build_transaction({
        'from': holder.address,
        'value': 0,
        'gasPrice': web3.to_wei(1, 'gwei'),
        'gas': int(config['SETTINGS']['gas_max']),
        'nonce': nonce
    })
    singed_main_tx = web3.eth.account.sign_transaction(tx_multicall, private_key=holder.private_key)
    tx_multicall_hash = web3.eth.send_raw_transaction(singed_main_tx.rawTransaction)


def task(holder):
    print('start')
    print(datetime.now())
    pause1 = random.randint(60, 180)
    print(f'waiting {pause1}....')
    amount = round(random.uniform(0.1, 1.5), 2)
    time.sleep(pause1)
    print(f'BUY {amount}')
    trade('buy', amount, holder)
    pause2 = random.randint(30, 300)
    print(f'waiting {pause2}....')
    time.sleep(pause2)
    trade('sell', 1, holder)
    print('end')
def main():
    holder1 = HOLDER(victim_address, victim_private)
    #schedule.every(10).minutes.do(task, holder=holder1)
    #while True:
    #    schedule.run_pending()
    #    time.sleep(1)








if __name__ == "__main__":
    main()
