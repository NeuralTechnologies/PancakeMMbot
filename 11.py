import random

# Function to generate an array of transactions
def generate_balanced_array(K, available_wallets):
    N = random.randint(5, 7)  # number of transactions in the series
    half_K = K / 2
    positive_part = generate_random_sum(N // 2, half_K)
    negative_part = generate_random_sum(N - N // 2, half_K)
    negative_part = [-x for x in negative_part]
    full_array = positive_part + negative_part
    random.shuffle(full_array)  # shuffle transactions randomly
    return full_array

# Function to distribute sum among array elements
def generate_random_sum(count, total_sum):
    amounts = [0] + sorted([random.random() for _ in range(count - 1)]) + [1]
    amounts = [round(total_sum * (amounts[i + 1] - amounts[i]), 2) for i in range(count)]
    return amounts

# Initialize initial balances of wallets
initial_usdt_balance = 1000
initial_ubx_balance = 2000  # initial UBX balance
wallets = {f"Wallet{i + 1}": {'USDT': initial_usdt_balance, 'UBX': initial_ubx_balance} for i in range(10)}

# Simulate 100 series of transactions
for i in range(500):
    K = random.randint(100, 500)  # transaction amount in the series in USDT
    transactions = generate_balanced_array(K, list(wallets.keys()))
    print(f"Series {i + 1} transactions:")
    total_positive, total_negative = 0, 0
    used_wallets = set()

    for transaction in transactions:
        available_wallets = [wallet for wallet in wallets if wallet not in used_wallets]
        if not available_wallets:
            print("No available wallets for transaction.")
            break

        if transaction > 0:
            wallet = min(available_wallets, key=lambda w: wallets[w]['USDT'])  # wallet with minimum USDT for buying
            total_positive += transaction
        else:
            wallet = min(available_wallets, key=lambda w: wallets[w]['UBX'])  # wallet with maximum UBX for selling
            total_negative += transaction

        used_wallets.add(wallet)  # add wallet to used list
        # Check if the transaction can be completed without negative balance
        if wallets[wallet]['USDT'] + transaction < 0 or wallets[wallet]['UBX'] + transaction < 0:
            print("Transaction cannot be completed. Insufficient balance.")
            continue

        # Update balances after transaction
        wallets[wallet]['USDT'] += transaction
        wallets[wallet]['UBX'] += -1*transaction*2  # Decrease UBX balance for selling UBX

        print(
            f"  Wallet {wallet}: {'Bought' if transaction > 0 else 'Sold'} {abs(transaction)} USDT, UBX balance adjusted by {abs(transaction)*2}")

    # Print total bought and sold after each series
    print(f"Total Bought: {total_positive:.2f} USDT, Total Sold: {total_negative:.2f} USDT")

    # Print current balances after each series
    print(f"After series {i + 1}:")
    for wallet, balances in wallets.items():
        print(f"  {wallet}: {balances['USDT']:.2f} USDT, {balances['UBX']:.2f} UBX")
