from flask import Flask, request, jsonify
import requests
import hashlib
import json
import time
from threading import Thread
from datetime import datetime

app = Flask(__name__)
main_server = 'https://laptop-ubuntu.tail6eefa7.ts.net'
miner_address = None

class Miner:
    def __init__(self):
        self.chain = []
        self.pending = []
        self.syncing = False
        self.last_block_index = 0
        self.cap_reached = False

    def sync_chain(self):
        try:
            res = requests.get(f"{main_server}/chain", timeout=5)
            if res.status_code == 200:
                self.chain = res.json()['chain']
            res_pending = requests.get(f"{main_server}/tx/pending", timeout=5)
            if res_pending.status_code == 200:
                self.pending = res_pending.json()
        except requests.exceptions.RequestException:
            self.print_status("Failed to sync with main server")

    def validate_chain(self):
        for i in range(1, len(self.chain)):
            prev = self.chain[i-1]
            curr = self.chain[i]
            if curr['previous_hash'] != hashlib.sha256(json.dumps(prev, sort_keys=True).encode()).hexdigest():
                return False
            if not self.valid_proof(prev['proof'], curr['proof']):
                return False
        return True

    @staticmethod
    def valid_proof(last, current):
        guess = f"{last}{current}".encode()
        return hashlib.sha256(guess).hexdigest().startswith('00000')

    def print_status(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def mine(self):
        while True:
            self.sync_chain()
            
            if self.chain and self.last_block_index != self.chain[-1]['index']:
                if self.last_block_index > 0:
                    self.print_status(f"New block detected: #{self.chain[-1]['index']}")
                self.last_block_index = self.chain[-1]['index']
            
            # Check if coin supply cap is reached
            res = requests.get(f"{main_server}/current_reward")
            if res.status_code == 200:
                block_reward_amount = res.json().get('reward', 0.0)
                if block_reward_amount <= 0 and not self.cap_reached:
                    self.print_status("The blockchain's coins supply has reached the limit (5,000,000 coins).")
                    self.cap_reached = True
                elif block_reward_amount > 0:
                    self.cap_reached = False
            else:
                block_reward_amount = 0.0
            
            if not self.syncing and self.pending:
                last = self.chain[-1]
                new_block = {
                    'index': len(self.chain) + 1,
                    'timestamp': time.time(),
                    'transactions': self.pending.copy(),
                    'proof': 0,
                    'previous_hash': hashlib.sha256(json.dumps(last, sort_keys=True).encode()).hexdigest()
                }

                # Add reward transaction only if allowed
                if block_reward_amount > 0:
                    new_block['transactions'].append({
                        'sender': '0',
                        'recipient': miner_address,
                        'amount': block_reward_amount,
                        'message': hashlib.sha256(b'Block reward').hexdigest()
                    })
                else:
                    self.print_status("Skipping reward transaction (cap reached)")

                self.print_status(f"Mining block #{new_block['index']} with {len(new_block['transactions'])} transactions...")
                
                start_time = time.time()
                attempts = 0
                while not self.valid_proof(last['proof'], new_block['proof']):
                    new_block['proof'] += 1
                    attempts += 1
                    if attempts % 1000 == 0:
                        self.sync_chain()
                        if not self.chain or self.chain[-1]['index'] != last['index']:
                            self.print_status("Block outdated. Restarting...")
                            break

                if self.valid_proof(last['proof'], new_block['proof']):
                    self.print_status(f"Block #{new_block['index']} solved! Proof: {new_block['proof']}")
                    self.print_status(f"Time taken: {time.time() - start_time:.2f} seconds")
                    res = requests.post(f"{main_server}/block/receive", json=new_block)
                    if res.status_code == 200:
                        self.print_status(f"Block #{new_block['index']} accepted by network!")
                        if block_reward_amount > 0:
                            self.print_status(f"Reward: {block_reward_amount} coins added to {miner_address}")
                        # Force sync to update pending transactions
                        self.sync_chain()
                    else:
                        self.print_status(f"Block #{new_block['index']} rejected by network")
            time.sleep(0.1)

miner = Miner()

@app.route('/receive_block', methods=['POST'])
def receive_block():
    block = request.get_json()
    miner.chain.append(block)
    # Sync pending transactions directly from server to avoid staleness
    miner.sync_chain()
    return 'Block received', 200

@app.route('/chain')
def chain():
    return jsonify(miner.chain), 200

if __name__ == '__main__':
    miner_address = input("Wallet Address: ")
    print('WELCOME TO ETCoin MINER')
    requests.post(f"{main_server}/nodes/register", json={'node': 'http://localhost:5001'})
    miner.sync_chain()
    Thread(target=miner.mine, daemon=True).start()
    app.run(port=5001)
