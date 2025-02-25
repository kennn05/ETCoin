apt update -y 

apt upgrade -y 

pkg update -y

pkg install python openssl -y

pkg upgrade  -y  

apt install python -y 

pkg install git -y 

pkg install rust -y 

pkg install clang -y 

pkg install make -y 

pkg install openssl -y 

pkg install libffi -y 

pip install flask 

pip install ecdsa 

pip install mnemonic 

pip install requests 

pip install cryptography 

pip install rich

echo "Type wallet to access wallet and miner for mining ETCoin" > ~/ins.txt 

git clone https://github.com/kennn05/ETCoin

echo "rm -rf ~/ETCoin && git clone https://github.com/kennn05/ETCoin " > ~/../usr/bin/etcupdate 

chmod +x ~/../usr/bin/etcupdate

echo "python ~/ETCoin/wallet.py" > ~/../usr/bin/wallet

echo "python ~/ETCoin/miner.py" > ~/../usr/bin/miner 

echo "python ~/ETCoin/price.py" > ~/../usr/bin/price

chmod +x ~/../usr/bin/price

chmod +x ~/../usr/bin/wallet

chmod +x ~/../usr/bin/miner 

wallet
