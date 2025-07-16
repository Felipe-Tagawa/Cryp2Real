import os

from web3 import Web3
from solcx import compile_source, install_solc
from dotenv import load_dotenv
from my_blockchain import PRIVATE_KEY, GANACHE_URL, admWallet
from utils import extract_interface, sign_n_send

# Carregar variáveis de ambiente
load_dotenv()

# Instalar a versão adequada do compilador Solidity
install_solc("0.8.19")

# Conectar ao Ganache
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
private_key = PRIVATE_KEY

# Ler o código Solidity que contém ambos os contratos
solidity_code = ""

# Lê todos os arquivos .sol da pasta Contract e combina em um único código
for filename in ["sistemaCliente.sol", "etherFlow.sol"]:
    path = os.path.join("../Contract", filename)
    with open(path, "r") as f:
        solidity_code += f.read() + "\n"

# Compilar os contratos usando compile_source com otimizações
compiled_contracts = compile_source(
    solidity_code,
    output_values=["abi", "bin"],
    solc_version="0.8.19",
    optimize=True,
    optimize_runs=200,
    via_ir=True  # Habilita o pipeline IR para resolver "Stack too deep"
)

# Extrair interfaces (ABI + bytecode) usando sua função extract_interface
sistema_cliente_abi, sistema_cliente_bytecode = extract_interface(compiled_contracts, "SistemaCliente")
new_ether_abi, new_ether_bytecode = extract_interface(compiled_contracts, "NewEther")

# 1. Deploy SistemaCliente
sistema_cliente_contract = w3.eth.contract(abi=sistema_cliente_abi, bytecode=sistema_cliente_bytecode)
nonce = w3.eth.get_transaction_count(admWallet)

tx = sistema_cliente_contract.constructor().build_transaction({
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
    "from": admWallet,
    "nonce": nonce,
})

receipt = sign_n_send(tx, PRIVATE_KEY)
sistema_cliente_address = receipt["contractAddress"]
print(f"[✔] SistemaCliente deployado em: {sistema_cliente_address}")

# 2. Deploy NewEther
new_ether_contract = w3.eth.contract(abi=new_ether_abi, bytecode=new_ether_bytecode)
nonce += 1

tx2 = new_ether_contract.constructor(sistema_cliente_address).build_transaction({
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
    "from": admWallet,
    "nonce": nonce,
    "value": w3.to_wei(1, "wei")  # Valor simbólico
})

receipt2 = sign_n_send(tx2, PRIVATE_KEY)
new_ether_address = receipt2["contractAddress"]
print(f"[✔] NewEther deployado em: {new_ether_address}")

# 3. Gerar arquivo de saída com ABIs e endereços
with open("deploy_output.py", "w") as f:
    f.write(f'''
sistema_cliente_address = "{sistema_cliente_address}"
new_ether_address = "{new_ether_address}"

sistema_cliente_abi = {sistema_cliente_abi}
new_ether_abi = {new_ether_abi}
''')

print("\n[✓] Arquivo 'deploy_output.py' gerado com sucesso!")
