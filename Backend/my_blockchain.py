from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

GANACHE_URL = "https://3e171eefab2b.ngrok-free.app" # "http://127.0.0.1:7545"
PRIVATE_KEY = "0x1f9f1feb9dd4a6fa9f7de741de664b2e41e834a7b9be63a04e1ae2ed8ee56a42"

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

account = w3.eth.accounts

admWallet = account[0]  # conta admin
ongWallet = account[2]  # conta ONG

# Criar nova conta para comerciante
nova_conta = Account.create()
merchantWallet = nova_conta.address
private_key_comerciante = nova_conta.key.hex()

private_key = PRIVATE_KEY
