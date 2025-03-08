from flask import Flask, request, jsonify
import requests
import hashlib
import json
import time
import os
from threading import Thread
from datetime import datetime

app = Flask(__name__)
main_server = 'https://etcoin-server.tail6eefa7.ts.net' 
#main_server = 'http://192.168.43.79:5000'
miner_address = None

def banner():
    print(f"""\033[95m
    ⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⢀⣀⡿⠿⠿⠿⠿⠿⠿⢿⣀⣀⣀⣀⣀⡀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠸⠿⣇⣀⣀⣀⣀⣀⣀⣸⠿⢿⣿⣿⣿⡇⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠻⠿⠿⠿⠿⠿⣿⣿⣀⡸⠿⢿⣿⡇⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣤⣿⣿⣿⣧⣤⡼⠿⢧⣤⡀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣤⣿⣿⣿⣿⠛⢻⣿⡇⠀⢸⣿⡇
    ⠀⠀⠀⠀⠀⠀⠀⠀⣤⣤⣿⣿⣿⣿⠛⠛⠀⢸⣿⡇⠀⢸⣿⡇
    ⠀⠀⠀⠀⠀⠀⢠⣤⣿⣿⣿⣿⠛⠛⠀⠀⠀⢸⣿⡇⠀⢸⣿⡇
    ⠀⠀⠀⠀⢰⣶⣾⣿⣿⣿⠛⠛⠀⠀⠀⠀⠀⠈⠛⢳⣶⡞⠛⠁
    ⠀⠀⢰⣶⣾⣿⣿⣿⡏⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠁⠀⠀
    ⢰⣶⡎⠉⢹⣿⡏⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⢸⣿⣷⣶⡎⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠉⠉⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    """)

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

    def valid_proof(self, last_proof, current_proof):
        difficulty = 3 + (len(self.chain) // 2016)
        guess = f"{last_proof}{current_proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash.startswith('0' * difficulty)

    def print_status(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def mine(self):
        while True:
            self.sync_chain()

            if self.chain and self.last_block_index != self.chain[-1]['index']:
                if self.last_block_index > 0:
                    self.print_status(f"Block #{self.chain[-1]['index']} Added into Blockchain")
                self.last_block_index = self.chain[-1]['index']

            res = requests.get(f"{main_server}/current_reward")
            block_reward_amount = res.json().get('reward', 0.0) if res.status_code == 200 else 0.0

            if block_reward_amount <= 0 and not self.cap_reached:
                self.print_status("Blockchain coin supply cap reached (1,000,000,000 ETC)")
                self.cap_reached = True
            elif block_reward_amount > 0:
                self.cap_reached = False

            if not self.syncing:
                last = self.chain[-1]
                new_block = {
                    'index': len(self.chain) + 1,
                    'timestamp': time.time(),
                    'transactions': self.pending.copy(),
                    'proof': 0,
                    'previous_hash': hashlib.sha256(json.dumps(last, sort_keys=True).encode()).hexdigest()
                }

                if block_reward_amount > 0:
                    new_block['transactions'].append({
                        'sender': '0',
                        'recipient': miner_address,
                        'amount': block_reward_amount,
                        'message': hashlib.sha256(b'Block reward').hexdigest()
                    })
                self.print_status(f"Found New Block!!")
                self.print_status(f"Mining block #{new_block['index']} with {len(new_block['transactions'])} txs")
                
                start_time = time.time()
                last_proof = last['proof']
                current_proof = 0
                total_attempts = 0
                last_hash_display = start_time
                prefix = f"{last_proof}".encode()
                
                while True:
                    guess = prefix + str(current_proof).encode()
                    guess_hash = hashlib.sha256(guess).hexdigest()
                    if self.valid_proof(last_proof, current_proof):
                        new_block['proof'] = current_proof
                        print(f"Block #{new_block['index']} solved in {time.time()-start_time:.2f}s")
                        res = requests.post(f"{main_server}/block/receive", json=new_block)
                        if res.status_code == 200:
                            self.print_status(f"Block accepted! Reward: {block_reward_amount} ETC")
                        break
                    current_proof += 1
                    total_attempts += 1
                    
                    # Update hashrate display every 0.1 seconds
                    current_time = time.time()
                    if current_time - last_hash_display >= 0.1:
                        elapsed = current_time - start_time
                        if elapsed > 0:
                            hashrate = total_attempts / elapsed
                            print(f"\rCurrent Hashrate: {hashrate:.2f} H/s  Last Hash: {guess_hash[:12]}...", end="", flush=True)
                            last_hash_display = current_time

                    # Check for new blocks every 500 attempts
                    if total_attempts % 800 == 0:
                        self.sync_chain()
                        if self.chain[-1]['index'] != new_block['index'] - 1:
                            self.print_status("Block has been mined by another miner.\nLooking for New block...")
                            break

miner = Miner()

@app.route('/receive_block', methods=['POST'])
def receive_block():
    block = request.get_json()
    miner.chain.append(block)
    miner.sync_chain()
    return 'Block received', 200

if __name__ == '__main__':
    os.system('clear')
    banner()
    miner_address = ("6842193366513bbe90b5178fafa706f565eefb662f465e0d28e32b94f7b6b541")
    os.system('clear')
    print('==============================================')
    print('\n        ETCoin MINER - Turbo v2\n')
    print('==============================================\n')
    banner()
    miner.sync_chain()
    Thread(target=miner.mine, daemon=True).start()
    app.run(port=5001)
