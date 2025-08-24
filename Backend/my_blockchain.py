from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv
from Backend.deploy_output import sistema_cliente_address, etherFlow_address, sistema_cliente_abi, etherFlow_abi

load_dotenv()

GANACHE_URL = "http://127.0.0.1:7545"
PRIVATE_KEY = "0xf585ecd681060deb9f54d4b0a6dad7b23b6a7ec774c2ede437b546610be3cdef"

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

account = w3.eth.accounts

admWallet = account[0]  # conta admin
merchantWallet = account[1] # conta comerciante
ongWallet = account[2]  # conta ONG

# Criar nova conta para comerciante
nova_conta = Account.create()
private_key_comerciante = nova_conta.key.hex()

private_key = PRIVATE_KEY

etherFlow = w3.eth.contract(address=etherFlow_address, abi=etherFlow_abi)
sistema_cliente = w3.eth.contract(address=sistema_cliente_address, abi=sistema_cliente_abi)
