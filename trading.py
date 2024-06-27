from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import schedule
from datetime import datetime, timezone, timedelta
from sqlalchemy.sql import func
import time
import json
import random
from const import *
import base64
from cryptography.fernet import Fernet
import numpy as np


def get_data_from_graph(subgraph, graphql_query):
    transport = AIOHTTPTransport(url=subgraph)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query = gql(graphql_query)
    return client.execute(query)


def get_yesterday_volume():
    try:
        result = get_data_from_graph(config['SETTINGS']['graphql_url'],
                                     config['SETTINGS']['graphql_query_yesterday_volume'])['poolDayDatas'][1][
            'volumeUSD']
        return float(result)
    except Exception as e:
        print(e)
        return None


def fetch_swaps(start_timestamp, end_timestamp):
    swaps = []
    first = 1000
    skip = 0
    while True:
        query = config['SETTINGS']['graphql_query'].format(first=first, skip=skip, start_timestamp=start_timestamp,
                                                           end_timestamp=end_timestamp)
        new_swaps = get_data_from_graph(config['SETTINGS']['graphql_url'], query).get('swaps', [])
        if not new_swaps:
            break
        swaps.extend(new_swaps)
        skip += first
    return swaps


def get_10_min_ago_volume(start_timestamp, end_timestamp):
    try:
        swaps = fetch_swaps(start_timestamp, end_timestamp)
        volume = 0
        for swap in swaps:
            volume = volume + abs(float(swap['amount0']))
        return volume
    except Exception as e:
        print(e)
        return None


# get_data_every_minute()
# schedule.every().minute.at(":00").do(get_data_every_minute)
# while True:
#    schedule.run_pending()
#    time.sleep(1)

def cal_amount_out(amount_in):
    amount_out = QUOTER_CONTRACT.functions.quoteExactInputSingle(
    (USDT_ADDRESS, UBX_TOKEN, amount_in, int(config['SETTINGS']['fee']), 0)
    ).call()
    return int(amount_out) - 1 
    
def trade(side, amount, holder):
    nonce = web3.eth.get_transaction_count(holder.address)
    if side == "buy":
        amount_out =  cal_amount_out(int(amount * 10 ** 18))
        payload = (USDT_ADDRESS, UBX_TOKEN, int(config['SETTINGS']['fee']), holder.address,
                   int(amount * 10 ** 18), amount_out, 0)
        tx = PANCAKE_ROUTER_CONTRACT_V3.functions.exactInputSingle(payload).build_transaction({
            'from': holder.address,
            'value': 0,
            'gasPrice': web3.to_wei(1, 'gwei'),
            'gas': int(config['SETTINGS']['gas_max']),
            'nonce': nonce
        })
    else:

        payload = (UBX_TOKEN, USDT_ADDRESS, int(config['SETTINGS']['fee']), holder.address,
                   int(amount * 10 ** 18), int(1000000), 0)

        tx = PANCAKE_ROUTER_CONTRACT_V3.functions.exactOutputSingle(payload).build_transaction({
            'from': holder.address,
            'value': 0,
            'gasPrice': web3.to_wei(1, 'gwei'),
            'gas': int(config['SETTINGS']['gas_max']),
            'nonce': nonce
        })

    tx_multicall = PANCAKE_ROUTER_CONTRACT_V3.functions.multicall(
        int(time.time() + 10000),
        [tx['data']]
    ).build_transaction({
        'from': holder.address,
        'value': 0,
        'gasPrice': web3.to_wei(1, 'gwei'),
        'gas': int(config['SETTINGS']['gas_max']),
        'nonce': nonce
    })
    singed_main_tx = web3.eth.account.sign_transaction(tx_multicall, private_key=holder.private_key)
    tx_multicall_hash = web3.eth.send_raw_transaction(singed_main_tx.rawTransaction)


def generate_balanced_array(K):
    N = random.randint(int(config['SETTINGS']['min_series_count']), int(config['SETTINGS']['max_series_count']))
    half_K = K / 2
    positive_part = generate_random_sum(N // 2, half_K)
    negative_part = generate_random_sum(N - N // 2, half_K)
    negative_part = [-x for x in negative_part]
    full_array = positive_part + negative_part
    random.shuffle(full_array)  # shuffle transactions randomly
    return full_array


# Function to distribute sum among array elements
def generate_random_sum(count, total_sum):
    random_points = sorted([random.random() for _ in range(count - 1)])

    # Добавление минимальной разницы между точками для избежания нулей
    min_diff = 0.01  # Минимальное значение разницы в долях от total_sum
    amounts = [0] + [min(max(random_points[i] - (i * min_diff), 0), 1) for i in range(count - 1)] + [1]

    # Расчёт финальных значений с округлением
    final_amounts = [round(total_sum * (amounts[i + 1] - amounts[i]), 2) for i in range(count)]

    # Убедимся, что никакие значения не равны нулю
    final_amounts = [amount if amount > 0 else 0.01 for amount in final_amounts]

    return final_amounts


def generate_unique_array(N, total_sum=480, min_val=16, max_val=479):
    if N * min_val > total_sum or N * max_val < total_sum:
        raise ValueError("Impossible to generate an array with these constraints.")

    # Генерируем начальный массив уникальных значений
    unique_numbers = np.random.choice(range(min_val, max_val + 1), N, replace=False)

    # Нормализуем сумму к нужному значению
    current_sum = np.sum(unique_numbers)
    scale = total_sum / current_sum
    scaled_numbers = np.floor(unique_numbers * scale).astype(int)

    # Корректируем сумму после масштабирования
    while np.sum(scaled_numbers) != total_sum:
        diff = total_sum - np.sum(scaled_numbers)
        indices_to_adjust = np.random.choice(np.arange(N), size=abs(diff), replace=True)
        for index in indices_to_adjust:
            if diff > 0 and scaled_numbers[index] < max_val:
                scaled_numbers[index] += 1
            elif diff < 0 and scaled_numbers[index] > min_val:
                scaled_numbers[index] -= 1

    return scaled_numbers.tolist()


def task(holder):
    print('start')
    print(datetime.now())
    # pause1 = random.randint(60, 180)
    # print(f'waiting {pause1}....')
    amount = round(random.uniform(0.1, 1.5), 2)
    # time.sleep(pause1)
    print(f'BUY {amount}')
    trade('buy', amount, holder)
    pause2 = random.randint(30, 300)
    print(f'waiting {pause2}....')
    time.sleep(pause2)
    trade('sell', 1, holder)
    print('end')


def get_target_10_min_volume():
    try:
        now = datetime.now(timezone.utc)
        start_timestamp = now - timedelta(minutes=12)
        end_timestamp = now - timedelta(minutes=2)
        start_timestamp = int(start_timestamp.timestamp())
        end_timestamp = int(end_timestamp.timestamp())
        volume_10_min = get_10_min_ago_volume(start_timestamp, end_timestamp)
        volume_yesterday = get_yesterday_volume()
        logger.info(f'The trading volume for the last 10 minutes of the BNB USDT pair is {volume_10_min} USDT')
        logger.info(f'The trading volume for yesterday for the BNB USDT pair is {volume_yesterday} USDT')
        target_10_min_volume = round(
            (volume_10_min / volume_yesterday) * float(config['SETTINGS']['target_day_volume']), 2)
        logger.info(f'The target daily volume of the system is {config['SETTINGS']['target_day_volume']} USDT')
        logger.info(f'The target system volume for the next 10 minutes is {target_10_min_volume} USDT')
        return target_10_min_volume
    except Exception as e:
        logger.info(f'The Graph error when receiving 10 minute trading volume for WBNB USDT {e}')
        return None


def decrypt_data(encrypted_data, key):
    key = base64.urlsafe_b64decode(key.encode('utf-8'))
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode()


def get_holder_wallets_from_db():
    try:
        db_session = db_manager.Session()
        holder_wallets = db_session.query(db_manager.Base.classes.wallets).filter(
            db_manager.Base.classes.wallets.is_master == False,
            db_manager.Base.classes.wallets.is_active == True).all()
        wallets = []
        for holder_wallet in holder_wallets:
            usdt_balance = web3.from_wei(USDT_CONTRACT.functions.balanceOf(holder_wallet.address).call(), 'ether')
            bnb_balance = web3.from_wei(web3.eth.get_balance(holder_wallet.address), 'ether')
            ubx_balance = UBX_CONTRACT.functions.balanceOf(holder_wallet.address).call()
            private_key = decrypt_data(holder_wallet.private_key, config['SETTINGS']['secret_key'])
            wallet = {
                'address': holder_wallet.address,
                'private_key': private_key,
                'BNB': float(bnb_balance),
                'UBX': float(ubx_balance),
                'USDT': float(usdt_balance)
            }
            wallets.append(wallet)
        return wallets
    except Exception as e:
        logger.info(f'Failed to get wallets from database: {e}')
        return None


def preparation_series():
    target_10_min_volume = get_target_10_min_volume()
    if target_10_min_volume is None:
        logger.info(f'The series of trades cannot be executed')
        return None

    transactions = generate_balanced_array(target_10_min_volume)
    logger.info(f'The 10 minute volume is distributed as follows: {transactions}')
    pauses_series = generate_unique_array((len(transactions) + 1))
    logger.info(f'Pauses between transactions within a series in seconds: {pauses_series}')
    wallets = get_holder_wallets_from_db()

    if wallets is None:
        logger.info(f'The series of trades cannot be executed')
        return None

    public_wallets = [{key: value for key, value in wallet.items() if key != 'private_key'} for wallet in wallets]
    for public_wallet in public_wallets:
        logger.info(
            f'{public_wallet['address']}:   BNB: {round(float(public_wallet['BNB']), 4)} USDT:{round(float(public_wallet['USDT']), 4)} UBX:{float(public_wallet['USDT'])}')

    used_wallets = set()
    series = []
    for transaction in transactions:
        available_wallets = [wallet for wallet in wallets if wallet['address'] not in used_wallets]
        if not available_wallets:
            logger.info("No available wallets for transaction.")
            return None
        if transaction > 0:
            wallet = min(available_wallets, key=lambda w: w['USDT'])
            # total_positive += transaction
        else:
            wallet = min(available_wallets, key=lambda w: w['UBX'])
            # total_negative += transaction

        used_wallets.add(wallet['address'])
        # Check if the transaction can be completed without negative balance
        if wallet['USDT'] + transaction < 0 or wallet['UBX'] + transaction < 0:
            logger.info("Transaction cannot be completed. Insufficient balance.")
            return None
        # Update balances after transaction
        # wallets[wallet]['USDT'] += transaction
        # wallets[wallet]['UBX'] += -1 * transaction * 2  # Decrease UBX balance for selling UBX
        trade = {f'{wallet['address']}': {transaction}}
        series.append(trade)
    return series, wallets, pauses_series



    # schedule.every(10).minutes.do(task, holder=holder1)
    # while True:
    #    schedule.run_pending()
    #    time.sleep(1)


if __name__ == "__main__":
    logger.info(f'Start date of the series: {datetime.now(timezone.utc)}')
    series, wallets, pauses_series = preparation_series()
    for index, item in enumerate(series):
        time.sleep(pauses_series[index])
        key = list(item.keys())[0]  # Получаем ключ текущего элемента
        value = next(iter(item[key]))  # Получаем значение по ключу
        wallet = [wallet for wallet in wallets if wallet['address'] == key]
        #print(wallet[0])
        #print(value)
        holder = HOLDER(wallet[0]['address'], wallet[0]['private_key'])
        if value > 0:
            trade('buy',value,holder)
            print('buy')
        else:
            trade('sell', abs(value), holder)
            print('sell')
        time.sleep(pauses_series[index+1])
        #print(key)

        # Предполагаем, что wallets - это словарь, где ключи соответствуют ключам в series

    logger.info(series)

# holder1 = HOLDER(victim_address, victim_private)
# trade('buy', 1000, holder1)
