import os
import requests
import json
from ecdsa import SigningKey, SECP256k1
import hashlib
from mnemonic import Mnemonic
from getpass import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import time
import glob
import threading

SERVER = 'https://etcoin-server.tail6eefa7.ts.net'
#SERVER = 'http://192.168.43.79:5000'

def banner():
    print("""\033[38;5;214m
    
    ⠀⠀⠀⠀⠀⠀⠀⣀⣤⣴⣶⣾⣿⣿⣿⣿⣷⣶⣦⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⣠⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣄⠀⠀⠀⠀⠀
    ⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀
    ⠀⠀⣴⣿⣿⣿⣿⣿⣿⣿⠟⠿⠿⡿⠀⢰⣿⠁⢈⣿⣿⣿⣿⣿⣿⣿⣿⣦⠀⠀
    ⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣤⣄⠀⠀⠀⠈⠉⠀⠸⠿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀
    ⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⢠⣶⣶⣤⡀⠀⠈⢻⣿⣿⣿⣿⣿⣿⣿⡆
    ⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠼⣿⣿⡿⠃⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣷
    ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⢀⣀⣀⠀⠀⠀⠀⢴⣿⣿⣿⣿⣿⣿⣿⣿⣿
    ⢿⣿⣿⣿⣿⣿⣿⣿⢿⣿⠁⠀⠀⣼⣿⣿⣿⣦⠀⠀⠈⢻⣿⣿⣿⣿⣿⣿⣿⡿
    ⠸⣿⣿⣿⣿⣿⣿⣏⠀⠀⠀⠀⠀⠛⠛⠿⠟⠋⠀⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⠇
    ⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⠇⠀⣤⡄⠀⣀⣀⣀⣀⣠⣾⣿⣿⣿⣿⣿⣿⣿⡟⠀
    ⠀⠀⠻⣿⣿⣿⣿⣿⣿⣿⣄⣰⣿⠁⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀
    ⠀⠀⠀⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠀⠀⠀
    ⠀⠀⠀⠀⠀⠙⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠋⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠻⠿⢿⣿⣿⣿⣿⡿⠿⠟⠛⠉⠀⠀⠀⠀⠀    \033[1;33m""")

class Wallet:
    def __init__(self):
        self.private_key = None
        self.address = None
        self.username = ''
        self.seed_phrase = ''
        self.balance_cache = None
        self.balance_lock = threading.Lock()

    def generate(self):
        mnemo = Mnemonic("english")
        self.seed_phrase = mnemo.generate()
        print(f"\033[38;5;214m\nWarning: Keep this safe\n\nSeedPhrase: {self.seed_phrase}\033[1;33m\n")
        print(f"\n==================================")
        seed = mnemo.to_seed(self.seed_phrase)
        self.private_key = SigningKey.from_string(seed[:32], curve=SECP256k1)
        self.address = hashlib.sha256(self.private_key.verifying_key.to_string()).hexdigest()
        self.username = input("\033[38;5;214mUsername: \033[1;33m")
        self._save_to_file()
        return self

    def _save_to_file(self):
        while True:
            pin = getpass("\033[38;5;214m\nPIN: \033[1;33m\n")
            if len(pin) != 6 or not pin.isdigit():
                print("\033[38;5;214mError: PIN must be 6 digits.\033[1;33m")
                continue
            break

        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
        key = base64.urlsafe_b64encode(kdf.derive(pin.encode()))
        fernet = Fernet(key)
        key_data = {
            'phrase': self.seed_phrase,
            'private_key': base64.b64encode(self.private_key.to_pem()).decode(),
            'username': self.username
        }
        encrypted = fernet.encrypt(json.dumps(key_data).encode())
        with open(f"{self.username}.wallet", 'wb') as f:
            f.write(base64.b64encode(salt) + b'\n' + encrypted)
        print(f"\033[38;5;214mInfo: Wallet saved as {self.username}.wallet\033[1;33m")
        print(f"\n==================================")
        time.sleep(2)
        os.system('clear')

    def load(self, path):
        attempt = 0
        max_attempts = 3
        while attempt < max_attempts:
            pin = getpass("\033[38;5;214m\nEnter PIN: \033[1;33m")
            try:
                with open(path, 'rb') as f:
                    salt, encrypted = f.read().split(b'\n', 1)
                salt = base64.b64decode(salt)
                kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
                key = base64.urlsafe_b64encode(kdf.derive(pin.encode()))
                fernet = Fernet(key)
                decrypted = fernet.decrypt(encrypted)
                key_data = json.loads(decrypted)
                self.private_key = SigningKey.from_pem(base64.b64decode(key_data['private_key']))
                self.address = hashlib.sha256(self.private_key.verifying_key.to_string()).hexdigest()
                self.username = key_data['username']
                self.seed_phrase = key_data['phrase']
                threading.Thread(target=self._preload_balance, daemon=True).start()
                return self
            except (ValueError, Exception):
                attempt += 1
                print("\033[38;5;214mError: Wrong PIN or corrupted file!\033[1;33m")
                if attempt < max_attempts:
                    print(f"\033[38;5;214mAttempts left: {max_attempts - attempt}\033[1;33m")
                else:
                    print("\033[38;5;214mInfo: Max attempts reached. Exiting load.\033[1;33m")
                    break
        return None

    def _preload_balance(self):
        while True:
            with self.balance_lock:
                res = requests.get(f"{SERVER}/chain")
                if res.status_code == 200:
                    chain = res.json().get('chain', [])
                    balance = sum(tx['amount'] for block in chain for tx in block.get('transactions', []) if tx['recipient'] == self.address) - \
                              sum(tx['amount'] for block in chain for tx in block.get('transactions', []) if tx['sender'] == self.address)
                    self.balance_cache = balance
                else:
                    self.balance_cache = 0
            time.sleep(30)

    def recover_from_seed(self, phrase):
        mnemo = Mnemonic("english")
        if not mnemo.check(phrase):
            raise ValueError("Invalid seed phrase")
        self.seed_phrase = phrase
        seed = mnemo.to_seed(phrase)
        self.private_key = SigningKey.from_string(seed[:32], curve=SECP256k1)
        self.address = hashlib.sha256(self.private_key.verifying_key.to_string()).hexdigest()
        self.username = input("\033[38;5;214mUsername: \033[1;33m")
        self._save_to_file()
        return self

    def send(self, recipient, amount, message=''):
        os.system('clear')
        banner()
        print("\033[38;5;214m\nSend ETCOIN\033[1;33m")
        print(f"\nFrom: {self.address}")
        print(f"Receiver address: {recipient}")
        print(f"Amount: {amount} ETC")
        confirm = input("\033[38;5;214m\nConfirm transaction (y/n): \033[1;33m").lower()
        if confirm != 'y':
            print("\033[38;5;214m\nTransaction cancelled\033[1;33m")
            print(f"\n==================================")
            time.sleep(2)
            return

        tx = {
            'sender': self.address,
            'recipient': recipient,
            'amount': amount,
            'message': hashlib.sha256(message.encode()).hexdigest()
        }
        tx_hash = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
        res = requests.post(f"{SERVER}/tx/new", json=tx)
        
        os.system('clear')
        banner()
        if res.status_code == 201:
            print("\033[38;5;214m\nTransaction Receipt\033[1;33m")
            print("═══════════════════════")
            print(f"\033[1;32mStatus: Success\033[1;33m")
            print(f"\033[1;37mFrom: {self.address}\033[1;33m")
            print(f"\033[1;37mReceiver address: {recipient}\033[1;33m")
            print(f"\033[1;35mAmount: {amount} ETC\033[1;33m")
            print(f"Tx Hash: {tx_hash}")
            print(f"\033[1;32mTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\033[1;33m")
            print("═══════════════════════")
        else:
            print("\033[38;5;214m\nTransaction Failed\033[1;33m")
            print(f"\033[1;31mError: {res.text}\033[1;33m")
            print(f"\n==================================")
        input("\033[38;5;214m\nPress Enter to continue\033[1;33m")

    def balance(self):
        with self.balance_lock:
            if self.balance_cache is not None:
                print(f"\033[38;5;214m\nBalance: \033[1;32m{self.balance_cache:.5f} ETC\033[1;33m")
            else:
                res = requests.get(f"{SERVER}/balance/{self.address}")
                balance = res.json().get('balance', 0)
                self.balance_cache = balance
                print(f"\033[38;5;214m\nBalance: \033[1;32m{balance:.5f} ETC\033[1;33m")
            print(f"\n==================================")

    def get_transaction_history(self):
        res = requests.get(f"{SERVER}/chain")
        if res.status_code != 200:
            return []
        chain = res.json().get('chain', [])
        history = []
        for block in chain:
            for tx in block.get('transactions', []):
                if tx.get('sender') == self.address or tx.get('recipient') == self.address:
                    decrypted_msg = "Block reward" if tx['sender'] == '0' else "User transaction"
                    history.append({
                        'block_index': block['index'],
                        'timestamp': block['timestamp'],
                        'transaction': tx,
                        'decrypted_message': decrypted_msg
                    })
        return history

    def blockchain_explorer(self):
        while True:
            os.system('clear')
            banner()
            print("\033[38;5;214m\nBlockchain Explorer\033[1;33m")
            print("\n1. Global Search")
            print("2. Network Stats")
            print("3. Export BlockChain")
            print("4. Search Transaction Hash")
            print("5. Recent blocks")
            print("6. Back")
            choice = input("\033[38;5;214m\nCommand: \033[1;33m")
            res = requests.get(f"{SERVER}/chain")
            chain = res.json().get('chain', []) if res.status_code == 200 else []
            res_pending = requests.get(f"{SERVER}/tx/pending")
            pending_txs = res_pending.json() if res_pending.status_code == 200 else []
            if choice == '5':
                self._show_blocks(chain[-20:])
            elif choice == '2':
                self._show_stats(chain)
            elif choice == '3':
                self._export_chain(chain)
            elif choice == '4':
                self._search_transaction_hash(chain, pending_txs)
            elif choice == '1':
                self._global_search(chain, pending_txs)
            elif choice == '6':
                break
            if not choice:
                continue
            print(f"\n==================================")

    def _show_blocks(self, blocks):
        os.system('clear')
        for block in reversed(blocks):
            current_hash = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
            print(f"\033[38;5;214m\nBlock {block['index']} | {time.ctime(block['timestamp'])}\033[1;33m")
            print(f"Prev: {block['previous_hash']}")
            print(f"Current Hash: {current_hash}")
            print(f"Proof: {block['proof']}")
            print(f"Transactions: {len(block.get('transactions', []))}")
            for tx in block.get('transactions', []):
                decrypted_msg = "Block reward" if tx['sender'] == '0' else "User transaction"
                sender_display = tx['sender'] if tx['sender'] != '0' else "Network (Reward)"
                receiver_display = tx['recipient'] if tx['recipient'] else "N/A"
                print(f"  Sender: {sender_display}")
                print(f"  Receiver: {receiver_display}")
                print(f"  Amount: {tx['amount']} ETC")
                print("  ---")
        print(f"\n==================================")
        input("\033[38;5;214m\nPress Enter to continue\033[1;33m")

    def _show_stats(self, chain):
        os.system('clear')
        total_supply = 1000000000  # Fixed total supply
        minted = sum(tx['amount'] for block in chain for tx in block.get('transactions', []) if tx['sender'] == '0')
        remaining = total_supply - minted
        print("\033[38;5;214m\nNetwork Stats\033[1;33m")
        print(f"Blocks: {len(chain)}")
        print(f"Transactions: {sum(len(b.get('transactions', [])) for b in chain)}")
        print(f"Mined: {minted:.2f} ETC")
        print(f"Remaining to Mine: {remaining:.2f} ETC")
        print(f"Total Supply: {total_supply} ETC")
        print(f"\n==================================")
        input("\033[38;5;214m\nPress Enter to continue\033[1;33m")

    def _export_chain(self, chain):
        filename = f"chain_{time.strftime('%Y-%m-%d %H:%M:%S')}.json"
        with open(filename, 'w') as f:
            json.dump(chain, f, indent=2)
        print(f"\033[38;5;214mInfo: Saved to {filename}\033[1;33m")
        print(f"\n==================================")
        time.sleep(2)

    def _show_full_details(self, chain):
        os.system('clear')
        print("\033[38;5;214m\nFull Blockchain Details (Last 10 Blocks)\033[1;33m")
        for block in chain[-10:]:
            current_hash = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
            print(f"\nBlock {block['index']} | {time.ctime(block['timestamp'])}")
            print(f"Prev: {block['previous_hash']}")
            print(f"Current Hash: {current_hash}")
            print(f"Proof: {block['proof']}")
            print(f"Transactions:")
            for tx in block.get('transactions', []):
                decrypted_msg = "Block reward" if tx['sender'] == '0' else "User transaction"
                sender_display = tx['sender'] if tx['sender'] != '0' else "Network (Reward)"
                receiver_display = tx['recipient'] if tx['recipient'] else "N/A"
                print(f"  Sender: {sender_display}")
                print(f"  Receiver: {receiver_display}")
                print(f"  Amount: {tx['amount']} ETC")
                print(f"  Message: {decrypted_msg}")
                print("  ---")
        print(f"\n==================================")
        input("\033[38;5;214m\nPress Enter to continue\033[1;33m")

    def _search_transaction_hash(self, chain, pending_txs):
        os.system('clear')
        tx_hash = input("\033[38;5;214mTransaction Hash: \033[1;33m")
        found = False
        # Search completed transactions
        for block in chain:
            for tx in block.get('transactions', []):
                tx_data = {
                    'sender': tx['sender'],
                    'recipient': tx['recipient'],
                    'amount': tx['amount'],
                    'message': tx['message']
                }
                calculated_hash = hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()
                if calculated_hash == tx_hash:
                    print(f"\033[38;5;214m\nTransaction Found in Block {block['index']}\033[1;33m")
                    print(f"Time: {time.ctime(block['timestamp'])}")
                    print(f"Sender: {tx['sender']}")
                    print(f"Receiver: {tx['recipient'] if tx['recipient'] else 'N/A'}")
                    print(f"Amount: {tx['amount']} ETC")
                    print(f"Message: {'Block reward' if tx['sender'] == '0' else 'User transaction'}")
                    print(f"Tx Hash: {calculated_hash}")
                    found = True
                    break
            if found:
                break
        # Search pending transactions
        if not found:
            for tx in pending_txs:
                tx_data = {
                    'sender': tx['sender'],
                    'recipient': tx['recipient'],
                    'amount': tx['amount'],
                    'message': tx['message']
                }
                calculated_hash = hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()
                if calculated_hash == tx_hash:
                    print(f"\033[38;5;214m\nTransaction Found in Pending\033[1;33m")
                    print(f"Sender: {tx['sender']}")
                    print(f"Receiver: {tx['recipient'] if tx['recipient'] else 'N/A'}")
                    print(f"Amount: {tx['amount']} ETC")
                    print(f"Message: {'User transaction'}")
                    print(f"Tx Hash: {calculated_hash}")
                    print(f"Status: Pending")
                    found = True
                    break
        if not found:
            print("\033[1;31mError: Transaction not found!\033[1;33m")
        print(f"\n==================================")
        input("\033[38;5;214m\nPress Enter to continue\033[1;33m")

    def _global_search(self, chain, pending_txs):
        os.system('clear')
        search_type = input("\033[38;5;214mSearch by (index/hash/address): \033[1;33m").lower()
        if search_type in ['index', 'i']:
            index = input("\033[38;5;214mBlock Index: \033[1;33m")
            try:
                block = next(b for b in chain if b['index'] == int(index))
                print(f"\033[38;5;214m\nBlock {block['index']} Found\033[1;33m")
                print(f"Time: {time.ctime(block['timestamp'])}")
                print(f"Prev: {block['previous_hash'][:12]}...")
                print(f"Proof: {block['proof']}")
                for tx in block.get('transactions', []):
                    print(f"  Sender: {tx['sender'][:8]}... -> Receiver: {tx['recipient'] if tx['recipient'] else 'N/A'}... : Amount: {tx['amount']} ETC")
            except (ValueError, StopIteration):
                print("\033[1;31mError: Block not found!\033[1;33m")
        elif search_type in ['hash', 'h']:
            block_hash = input("\033[38;5;214mBlock Hash: \033[1;33m")
            block = next((b for b in chain if hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest() == block_hash), None)
            if block:
                print(f"\033[38;5;214m\nBlock {block['index']} Found\033[1;33m")
                print(f"Time: {time.ctime(block['timestamp'])}")
                print(f"Prev: {block['previous_hash'][:12]}...")
                print(f"Proof: {block['proof']}")
                for tx in block.get('transactions', []):
                    print(f"  Sender: {tx['sender'][:8]}... -> Receiver: {tx['recipient'] if tx['recipient'] else 'N/A'}... : Amount: {tx['amount']} ETC")
            else:
                print("\033[1;31mError: Block not found!\033[1;33m")
        elif search_type in ['address', 'a']:
            target_address = input("\033[38;5;214mWallet Address: \033[1;33m")
            balance = 0.0
            transactions = []
            for block in chain:
                for tx in block.get('transactions', []):
                    if tx['recipient'] == target_address:
                        balance += tx['amount']
                    if tx['sender'] == target_address:
                        balance -= tx['amount']
                    if tx['sender'] == target_address or tx['recipient'] == target_address:
                        decrypted_msg = "Block reward" if tx['sender'] == '0' else "User transaction"
                        transactions.append({
                            'timestamp': block['timestamp'],
                            'sender': tx['sender'],
                            'receiver': tx['recipient'],
                            'amount': tx['amount'],
                            'message': decrypted_msg,
                            'block_index': block['index']
                        })
            print(f"\033[38;5;214m\nWallet Balance & Transactions for {target_address}\033[1;33m")
            print(f"Balance: {balance:.5f} ETC")
            print(f"Transaction History:")
            for tx in transactions:
                print(f"\n  Time: {time.ctime(tx['timestamp'])} | Block {tx['block_index']}")
                print(f"  Sender: {tx['sender']}")
                print(f"  Receiver: {tx['receiver']}")
                print(f"  Amount: {tx['amount']} ETC")
                print(f"  Message: {tx['message']}")
        else:
            print("\033[1;31mError: Invalid search type! Use 'index', 'hash', or 'address'.\033[1;33m")
        print(f"\n==================================")
        input("\033[38;5;214m\nPress Enter to continue\033[1;33m")

def menu():
    wallet = None
    while True:
        if not wallet:
            os.system('clear')
            banner()
            print("\n========= ETCoin Wallet ========\n")
            print("\033[38;5;214m\nETCoin Wallet\033[1;33m")
            print("\n1. Create Wallet")
            print("2. Login Wallet")
            print("3. Recover Wallet")
            print("4. Exit")
            print("\n================================\n")
            choice = input("\033[38;5;214m\nCommand: \033[1;33m")
            if choice == '1':
                wallet = Wallet().generate()
            elif choice == '2':
                wallets = glob.glob('*.wallet')
                if not wallets:
                    print("\033[38;5;214mError: No wallets found!\033[1;33m")
                    print(f"\n==================================")
                    time.sleep(2)
                    continue
                os.system('clear')
                banner()
                print("\n========= ETCoin Wallet ========\n")
                print("\033[38;5;214m\nAvailable Wallets:\033[1;33m\n")
                for i, w in enumerate(wallets, 1):
                    print(f"{i}. {w}")
                try:
                    sel = int(input("\033[38;5;214m\nSelect number :  \033[1;33m")) - 1
                    wallet = Wallet().load(wallets[sel])
                    if not wallet:
                        wallet = None
                except (ValueError, IndexError):
                    print("\033[38;5;214mError: Invalid choice!\033[1;33m")
                    print(f"\n==================================")
                    time.sleep(2)
                except:
                    print("\033[38;5;214mError: An unexpected error occurred!\033[1;33m")
                    print(f"\n==================================")
                    time.sleep(2)
            elif choice == '3':
                phrase = input("\033[38;5;214mSeed Phrase: \033[1;33m")
                try:
                    wallet = Wallet().recover_from_seed(phrase)
                except Exception as e:
                    print(f"\033[1;31mError: {e}\033[1;33m")
                    print(f"\n==================================")
                    time.sleep(2)
            elif choice == '4':
                break
        else:
            os.system('clear')
            banner()
            print("\n========= ETCoin Wallet ========\n")
            print(f"\033[38;5;214m\nUsername: {wallet.username}\033[1;33m")
            print(f"Address: \033[1;37m{wallet.address}\033[1;33m")
            wallet.balance()
            print("\n1. Send ETC")
            print("2. History")
            print("3. Explorer")
            print("4. Show Key")
            print("5. Show Seed")
            print("6. Logout")
            print("\n=================================\n")
            cmd = input("\033[38;5;214m\nCommand: \033[1;33m")
            if cmd == '1':
                os.system('clear')
                banner()
                print("\n========= ETCoin Wallet ========\n")
                print("\033[38;5;214m\nSend ETCOIN\033[1;33m")
                recipient = input("\033[38;5;214mReceiver address: \033[1;33m")
                amount = float(input("\033[38;5;214mAmount: \033[1;33m"))
                message = ("\033[38;5;214mMessage (optional): \033[1;33m")
                wallet.send(recipient, amount, message)
            elif cmd == '2':
                os.system('clear')
                print("\n========= ETCoin Wallet ========\n")
                print("\033[38;5;214m\nTransaction History\033[1;33m")
                for entry in wallet.get_transaction_history():
                    tx = entry['transaction']
                    print(f"\nTime: {time.ctime(entry['timestamp'])} | Block {entry['block_index']}")
                    print(f"Sender: {tx['sender']}")
                    print(f"Receiver: {tx['recipient']}")
                    print(f"Amount: {tx['amount']} ETC")
                    print(f"Message: {entry['decrypted_message']}")
                print(f"\n==================================")
                input("\033[38;5;214m\nPress Enter to continue\033[1;33m")
            elif cmd == '3':
                wallet.blockchain_explorer()
            elif cmd == '4':
                os.system('clear')
                banner()
                print("\n========= ETCoin Wallet ========\n")
                print(f"\033[38;5;214m\nPrivate Key: {wallet.private_key.to_pem().decode()}\033[1;33m")
                print(f"\n==================================")
                input("\033[38;5;214m\nPress Enter to continue\033[1;33m")
            elif cmd == '5':
                os.system('clear')
                print(f"\033[38;5;214m\nSeed: \033[38;5;214m{wallet.seed_phrase}\033[1;33m")
                print(f"\n==================================")
                input("\033[38;5;214m\nPress Enter to continue\033[1;33m")
            elif cmd == '6':
                wallet = None
            if not cmd:
                continue

if __name__ == '__main__':
    menu()
