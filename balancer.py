import schedule
from datetime import datetime, timezone
from cryptography.fernet import Fernet
import base64
from const import *
from decimal import Decimal


def decrypt_data(encrypted_data, key):
    key = base64.urlsafe_b64decode(key.encode('utf-8'))
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode()


def encrypt_data(data, key):
    key = base64.urlsafe_b64decode(key.encode('utf-8'))
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data


class HOLDER_WALLET:
    def __init__(self, address, private_key):
        self.address = address
        self.private_key = private_key


def create_wallet(db_session, master: bool):
    wallet = web3.eth.account.create()
    encrypted_private_key = encrypt_data(wallet._private_key.hex(), config['SETTINGS']['secret_key'])
    new_row = db_manager.Base.classes.wallets()
    new_row.address = wallet.address
    new_row.private_key = encrypted_private_key.decode('utf-8')
    new_row.date_create = datetime.now(timezone.utc)
    new_row.is_master = master
    new_row.is_active = True
    db_session.add(new_row)
    db_session.commit()
    holder_wallet = HOLDER_WALLET(wallet.address, wallet._private_key.hex())
    return holder_wallet


def check_wallet_balance(address, N):
    bnb_balance = web3.from_wei(web3.eth.get_balance(address), 'ether')

    print("BNB Balance:", bnb_balance)
    print(N * config['SETTINGS']['start_bnb_balance'] + config['SETTINGS']['min_bnb_balance'])
    if bnb_balance < N * config['SETTINGS']['start_bnb_balance'] + config['SETTINGS']['min_bnb_balance']:
        return False

    usdt_balance = web3.from_wei(USDT_CONTRACT.functions.balanceOf(address).call(), 'ether')
    print("USDT Balance:", usdt_balance)
    print(N * config['SETTINGS']['start_usdt_balance'])
    if usdt_balance < N * config['SETTINGS']['start_usdt_balance']:
        return False

    print("USDT Balance:", web3.from_wei(usdt_balance, 'ether'))

    ubx_balance = UBX_CONTRACT.functions.balanceOf(address).call() * 10 ** UBX_DECIMAL
    if ubx_balance < N * config['SETTINGS']['start_ubx_balance']:
        return False

    print("UBX Balance:", ubx_balance)
    return True


def send_currency(from_address, to_address, amount, currency, private_key, nonce):
    # nonce = web3.eth.get_transaction_count(from_address)
    if currency == 'UBX':
        contract = UBX_CONTRACT
        DECIMAL = UBX_DECIMAL
    if currency == 'USDT':
        contract = USDT_CONTRACT
        DECIMAL = USDT_DECIMAL
    # Проверяем, что валюта это BNB или токен
    if currency == 'BNB':
        # Создаем транзакцию для отправки BNB
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': web3.to_wei(amount, 'ether'),
            'gas': 21000,
            'gasPrice': web3.to_wei('1', 'gwei')
        }
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash)
        return web3.to_hex(tx_hash)
    else:
        # Создаем транзакцию для отправки токена
        tx = contract.functions.transfer(to_address, int(amount * (10 ** DECIMAL))).build_transaction({
            'chainId': 56,
            'gas': 100000,
            'gasPrice': web3.to_wei('1', 'gwei'),
            'nonce': nonce,
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash)
        return web3.to_hex(tx_hash)


def approve_usdt(holder_wallet):
    nonce = web3.eth.get_transaction_count(holder_wallet.address)
    amount = 2**256 - 1
    txn = USDT_CONTRACT.functions.approve(PANCAKE_ROUTER_ADDRESS_V3, amount).build_transaction({
        'chainId': 56,  # Mainnet
        'gas': 200000,
        'gasPrice': web3.to_wei('1', 'gwei'),
        'nonce': nonce
    })
    signed_txn = web3.eth.account.sign_transaction(txn, private_key=holder_wallet.private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash)
    return web3.to_hex(tx_hash)


def approve_ubx(holder_wallet):
    nonce = web3.eth.get_transaction_count(holder_wallet.address)
    amount = 2**256 - 1
    txn = UBX_CONTRACT.functions.approve(PANCAKE_ROUTER_ADDRESS_V3, amount).build_transaction({
        'chainId': 56,  # Mainnet
        'gas': 200000,
        'gasPrice': web3.to_wei('1', 'gwei'),
        'nonce': nonce
    })
    signed_txn = web3.eth.account.sign_transaction(txn, private_key=holder_wallet.private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash)
    return web3.to_hex(tx_hash)
def create_holders(N, db_session):
    # Create N wallet holders
    wallets = [create_wallet(db_session, False) for i in range(N)]
    # Get a master wallet
    master_wallet = db_session.query(db_manager.Base.classes.wallets).filter(
        db_manager.Base.classes.wallets.is_master == True,
        db_manager.Base.classes.wallets.is_active == True).all()
    # Проверка условия: должен быть ровно один активный мастер-кошелек
    if len(master_wallet) != 1:
        error_message = "Должен быть ровно один активный мастер-кошелек."
        print(error_message)  # Или использовать logging для логирования ошибки
        return  # Выход из функции

    if not check_wallet_balance(master_wallet[0].address, N):
        print('Не достаточно денег на мастер кошелке ')
        return

    master_wallet = master_wallet[0]
    nonce = web3.eth.get_transaction_count(master_wallet.address)
    master_private_key = decrypt_data(master_wallet.private_key, config['SETTINGS']['secret_key'])
    for wallet in wallets:
        send_currency(master_wallet.address, wallet.address, config['SETTINGS']['start_bnb_balance'], 'BNB',
                      master_private_key, nonce)
        nonce = nonce + 1
        send_currency(master_wallet.address, wallet.address, config['SETTINGS']['start_usdt_balance'], 'USDT',
                      master_private_key, nonce)
        nonce = nonce + 1

        send_currency(master_wallet.address, wallet.address, config['SETTINGS']['start_ubx_balance'], 'UBX',
                      master_private_key, nonce)
        nonce = nonce + 1
        approve_ubx(wallet)
        approve_usdt(wallet)



def return_money_to_master_from_holder(holder, master_wallet):
    # Весь баланс UBX
    print(holder.address)

    nonce = web3.eth.get_transaction_count(holder.address)
    usdt_balance = web3.from_wei(USDT_CONTRACT.functions.balanceOf(holder.address).call(), 'ether')

    print(usdt_balance)
    if usdt_balance > 0:
        bnb_balance = web3.from_wei(web3.eth.get_balance(holder.address), 'ether') - Decimal('0.00006')
        if bnb_balance > 0:
            send_currency(holder.address, master_wallet.address, usdt_balance, 'USDT',
                          holder.private_key, nonce)
            nonce = nonce + 1
    ubx_balance = UBX_CONTRACT.functions.balanceOf(holder.address).call()
    print(ubx_balance)
    if ubx_balance > 0:
        bnb_balance = web3.from_wei(web3.eth.get_balance(holder.address), 'ether') - Decimal('0.00006')
        if bnb_balance > 0:
            send_currency(holder.address, master_wallet.address, ubx_balance, 'UBX',
                          holder.private_key, nonce)
            nonce = nonce + 1
    bnb_balance = web3.from_wei(web3.eth.get_balance(holder.address), 'ether') - Decimal('0.000021')
    print(bnb_balance)
    if bnb_balance > 0:
        send_currency(holder.address, master_wallet.address, bnb_balance, 'BNB',
                      holder.private_key, nonce)


def return_all_money_to_master(db_session):
    holder_wallets = db_session.query(db_manager.Base.classes.wallets).filter(
        db_manager.Base.classes.wallets.is_master == False,
        db_manager.Base.classes.wallets.is_active == False).all()
    new_master = create_wallet(db_session, True)

    for holder in holder_wallets:
        h = HOLDER_WALLET(holder.address, decrypt_data(holder.private_key, config['SETTINGS']['secret_key']))
        return_money_to_master_from_holder(h, new_master)
        holder.is_active = False
    db_session.commit()
    return new_master

db_session = db_manager.Session()
master_wallet = db_session.query(db_manager.Base.classes.wallets).filter(
    db_manager.Base.classes.wallets.is_master == True,
    db_manager.Base.classes.wallets.is_active == True).all()

master_private_key = decrypt_data(master_wallet[0].private_key, config['SETTINGS']['secret_key'])
print(master_private_key)
#create_holders(10,db_session)
#return_all_money_to_master(db_session)
db_session.close()
