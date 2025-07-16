# Funções auxiliares

from Backend.FlaskProject.Backend.my_blockchain import w3
import requests

# Função de lista de todas as contas:
def listAllAccounts():
    print(w3.eth.accounts)  # lista todas as contas do Ganache
    for conta in w3.eth.accounts:
        saldo = w3.from_wei(w3.eth.get_balance(conta), 'ether')
        print(conta, saldo)

# Função para assinar e enviar uma transação:
def sign_n_send(tx, private_key):
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transação enviada. Hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

# Função de integração do contrato Solidity com Python
def extract_interface(compiled_contracts, contract_name):
    # Cria o identificador do contrato no formato padrão do compilador Solidity
    # "<stdin>:NomeDoContrato" indica que o código foi compilado a partir da entrada padrão (concatenação dos arquivos .sol)
    contract_id = f"<stdin>:{contract_name}"

    # Acessa os dados do contrato específico usando o identificador
    interface = compiled_contracts[contract_id]

    # Retorna a ABI (interface) e o bytecode (código compilado)
    # ABI: necessária para interagir com o contrato após deploy
    # BIN: necessário para fazer o deploy do contrato na blockchain
    return interface["abi"], interface["bin"]

# Função que indica a cotação atual (ether - BRL)
def get_eth_to_brl():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "ethereum", "vs_currencies": "brl"}
    response = requests.get(url, params=params)
    data = response.json()
    return data["ethereum"]["brl"]
