from flask import Flask, jsonify, request
import hashlib
import json
from time import time
from threading import Lock
import requests
import os

app = Flask(__name__)
lock = Lock()

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_txs = []
        self.nodes = set()
        self.load_data()
        
        if not self.chain:
            self.create_genesis()

    def load_data(self):
        if os.path.exists('blockchain.json'):
            with open('blockchain.json') as f:
                data = json.load(f)
                self.chain = data['chain']
                self.pending_txs = data['pending']
                self.nodes = set(data.get('nodes', []))
        else:
            self.create_genesis()

    def save_data(self):
        data = {
            'chain': self.chain,
            'pending': self.pending_txs,
            'nodes': list(self.nodes)
        }
        with open('blockchain.json', 'w') as f:
            json.dump(data, f, indent=2)

    def create_genesis(self):
        genesis = {
            'index': 1,
            'timestamp': time(),
            'transactions': [{
                'sender': '0',
                'recipient': '2f2f927ff80fb4c2f48fb3ea603cedbfe7b4a5132e97462b77e0e7618ef6c09c',
                'amount': 0,
                'message': 'genesis'
            }],
            'proof': 0,
            'previous_hash': '0'
        }
        self.chain.append(genesis)
        self.save_data()

    def total_coins(self):
        total = 0.0
        for block in self.chain:
            for tx in block.get('transactions', []):
                if tx['sender'] == '0':
                    total += tx['amount']
        return total

    def validate_block(self, block):
        last = self.chain[-1]
        if block['previous_hash'] != self.hash(last):
            return False
        if not self.valid_proof(last['proof'], block['proof']):
            return False
        return True

    def valid_proof(self, last_proof, current_proof):
        difficulty = self.get_difficulty()
        guess = f"{last_proof}{current_proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash.startswith('0' * difficulty)

    def get_difficulty(self):
        if not self.chain:
            return 3
        return 3 + (len(self.chain) // 2016)

    @staticmethod
    def hash(block):
        return hashlib.sha256(
            json.dumps(block, sort_keys=True).encode()
        ).hexdigest()

    def sync_nodes(self, block):
        for node in self.nodes.copy():
            try:
                requests.post(f"{node}/receive_block", json=block)
            except:
                self.nodes.remove(node)

    def get_balance(self, address):
        balance = 0.0
        for block in self.chain:
            for tx in block.get('transactions', []):
                if tx['recipient'] == address:
                    balance += tx['amount']
                if tx['sender'] == address:
                    balance -= tx['amount']
        return balance

blockchain = Blockchain()

@app.route('/chain')
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }), 200

@app.route('/tx/new', methods=['POST'])
def new_tx():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    sender = values['sender']
    recipient = values['recipient']
    amount = values['amount']
    
    if sender == recipient:
        return 'Cannot send to yourself', 400
    
    if amount <= 0:
        return 'Amount must be positive', 400
    
    if sender == '0':
        return 'Invalid sender address', 400
    
    balance = blockchain.get_balance(sender)
    
    pending_spent = sum(
        tx['amount'] for tx in blockchain.pending_txs
        if tx.get('sender') == sender
    )
    
    available_balance = balance - pending_spent
    
    if available_balance < amount:
        return f'Insufficient balance. Available: {available_balance:.5f}', 400
    
    with lock:
        blockchain.pending_txs.append(values)
        blockchain.save_data()
    return '\nTransaction Successful', 201

@app.route('/tx/pending')
def pending_txs():
    return jsonify(blockchain.pending_txs), 200

@app.route('/block/receive', methods=['POST'])
def receive_block():
    block = request.get_json()
    with lock:
        current_total = blockchain.total_coins()
        remaining = 1000000000 - current_total

        allowed_reward = 0.0
        if remaining > 0:
            block_index = block['index']
            period = (block_index - 1) // 2016
            base_reward = 50 * (0.5 ** period)
            allowed_reward = min(base_reward, remaining)

        reward_transactions = [tx for tx in block.get('transactions', []) if tx.get('sender') == '0']
        
        if allowed_reward > 0:
            if len(reward_transactions) != 1:
                return 'Invalid block: must have exactly one reward transaction', 400
            reward_tx = reward_transactions[0]
            if reward_tx != block['transactions'][-1]:
                return 'Invalid block: reward transaction must be last', 400
            if reward_tx['amount'] != allowed_reward:
                return f'Invalid reward amount: expected {allowed_reward}, got {reward_tx["amount"]}', 400
            txs_to_remove = block.get('transactions', [])[:-1]
        else:
            if len(reward_transactions) > 0:
                return 'Invalid block: no reward allowed but reward transaction present', 400
            txs_to_remove = block.get('transactions', [])
        
        if blockchain.validate_block(block):
            blockchain.chain.append(block)
            block_txs = [json.dumps(tx, sort_keys=True) for tx in txs_to_remove]
            blockchain.pending_txs = [
                tx for tx in blockchain.pending_txs
                if json.dumps(tx, sort_keys=True) not in block_txs
            ]
            blockchain.save_data()
            return 'Block accepted', 200
        else:
            return 'Invalid block', 400

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    node = values.get('node')
    if not node:
        return 'Error: Need valid node URL', 400

    blockchain.nodes.add(node)
    blockchain.save_data()
    return jsonify(list(blockchain.nodes)), 201

@app.route('/nodes')
def list_nodes():
    return jsonify(list(blockchain.nodes)), 200

@app.route('/balance/<address>')
def balance(address):
    balance = blockchain.get_balance(address)
    return jsonify({'balance': round(balance, 5)}), 200

@app.route('/current_reward')
def current_reward():
    current_total = blockchain.total_coins()
    remaining = 1000000000 - current_total
    if remaining <= 0:
        return jsonify({'reward': 0.0}), 200
    
    next_block_index = len(blockchain.chain) + 1
    period = (next_block_index - 1) // 2016
    base_reward = 50 * (0.5 ** period)
    allowed_reward = min(base_reward, remaining)
    
    return jsonify({'reward': allowed_reward}), 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
