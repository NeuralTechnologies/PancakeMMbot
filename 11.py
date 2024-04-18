import random


# Функция для создания массива сделок
def generate_balanced_array(K):
    N = random.randint(5, 7)  # число транзакций в серии
    half_K = K / 2
    positive_part = generate_random_sum(N // 2, half_K)
    negative_part = generate_random_sum(N - N // 2, half_K)
    negative_part = [-x for x in negative_part]
    full_array = positive_part + negative_part
    random.shuffle(full_array)  # случайное распределение транзакций
    return full_array


# Функция для распределения суммы по элементам массива
def generate_random_sum(count, total_sum):
    amounts = [0] + sorted([random.random() for _ in range(count - 1)]) + [1]
    amounts = [round(total_sum * (amounts[i + 1] - amounts[i]), 2) for i in range(count)]
    return amounts


# Инициализация начальных балансов кошельков
initial_usdt_balance = 1000
initial_ubx_balance = 2000  # начальный баланс UBX
wallets = {f"Wallet{i + 1}": {'USDT': initial_usdt_balance, 'UBX': initial_ubx_balance} for i in range(10)}
print(generate_random_sum(5,100))


# Моделирование 100 серий транзакций
for i in range(100):
    K = random.randint(100, 500)  # сумма сделок в серии в USDT
    transactions = generate_balanced_array(K)
    print(f"Series {i + 1} transactions:")
    total_positive, total_negative = 0, 0

    for transaction in transactions:
        if transaction > 0:
            wallet = min(wallets, key=lambda w: wallets[w]['USDT'])  # кошелек с минимальным USDT для покупки
            total_positive += transaction
        else:
            wallet = max(wallets, key=lambda w: wallets[w]['UBX'])  # кошелек с максимальным USDT для продажи
            total_negative += transaction

        wallets[wallet]['USDT'] += transaction
        wallets[wallet]['UBX'] += transaction * 2  # UBX изменяется в два раза быстрее, т.к. стоимость в два раза меньше

        print(
            f"  Wallet {wallet}: {'Bought' if transaction > 0 else 'Sold'} {abs(transaction)} USDT, UBX balance adjusted by {abs(transaction * 2)}")

    # Вывод баланса покупок и продаж после каждой серии
    print(f"Total Bought: {total_positive:.2f} USDT, Total Sold: {total_negative:.2f} USDT")

    # Вывод текущих балансов после каждой серии
    print(f"After series {i + 1}:")
    for wallet, balances in wallets.items():
        print(f"  {wallet}: {balances['USDT']:.2f} USDT, {balances['UBX']:.2f} UBX")

# Примечание: Баланс USDT и UBX должен обрабатываться с учётом возможности их ухода в минус, если это важно.
