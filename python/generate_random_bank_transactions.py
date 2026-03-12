# generate random bank transactions
import random
from datetime import datetime, timedelta    

def generate_random_transaction():
    transaction_types = ['deposit', 'withdrawal', 'transfer']
    amounts = [round(random.uniform(10.0, 1000.0), 2) for _ in range(5)]
    
    transaction = {
        'type': random.choice(transaction_types),
        'amount': random.choice(amounts),
        'date': datetime.now() - timedelta(days=random.randint(1, 30)),
        'description': f"{random.choice(['Grocery', 'Salary', 'Rent', 'Utilities', 'Entertainment'])} payment"
    }
    
    return transaction

def generate_random_transactions(num_transactions=10):
    transactions = []
    for _ in range(num_transactions):
        transactions.append(generate_random_transaction())
    return transactions 