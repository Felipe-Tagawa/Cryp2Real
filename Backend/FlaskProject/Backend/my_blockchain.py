# pip install dotenv
# pip install web3
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv # carregar de arquivos.env

load_dotenv()

GANACHE_URL = "HTTP://127.0.0.1:7545"
PRIVATE_KEY = "0x1f9f1feb9dd4a6fa9f7de741de664b2e41e834a7b9be63a04e1ae2ed8ee56a42"
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
account = w3.eth.accounts
admWallet = account[0] # "0xD367327eECdA3e961f4c849ecfC6Aaf38844920C"
# Criar conta nova para comerciante
nova_conta = Account.create()
merchantWallet = nova_conta.address
private_key_comerciante = nova_conta.key.hex()
# merchantWallet = account[1] # "0x5435f2DB7d42635225FbE2D9B356B693e1F53D2F"
ongWallet = account[2] # "0xb0160622Ae02870C1559683dd25Bd36310D9fb21"

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
private_key = PRIVATE_KEY
