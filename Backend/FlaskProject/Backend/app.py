from eth_account import Account
from flask import Flask, jsonify, request
from flask_cors import CORS
from Backend.FlaskProject.Backend.deploy_contract import receipt
from Backend.FlaskProject.Backend.deploy_output import sistema_cliente_address, new_ether_address, sistema_cliente_abi, new_ether_abi
from Backend.FlaskProject.Backend.utils import sign_n_send, listAllAccounts, get_eth_to_brl
from Backend.FlaskProject.Backend.my_blockchain import w3, admWallet, private_key, merchantWallet
import time

if w3.is_connected():
    print("Conectado com sucesso ao Ganache!")
else:
    print("Não conectado com Ganache!")

contract = w3.eth.contract(address=new_ether_address, abi=new_ether_abi)
sistema_cliente = w3.eth.contract(address=sistema_cliente_address, abi=sistema_cliente_abi)

print(merchantWallet)

# listAllAccounts() -- Uso p/ Debug

# Criar um dicionário para inserir as contas:
contas_usuarios = {}

app = Flask(__name__)
CORS(app) # Permite requisições
@app.route('/')
def run():  # put application's code here
    return 'API funcionando com sucesso!'

# Registrar um novo cliente:

@app.route("/registrarCliente", methods=["POST"])
def registro_cliente():
    print("\n=== DADOS RECEBIDOS ===")
    print("Headers:", request.headers)
    print("Corpo (raw):", request.data)  # Verifique se os dados chegam

    data = request.get_json()
    print("JSON parseado:", data)  # Confira se o JSON foi interpretado


    if not data:
        return jsonify({"erro": "Dados JSON não fornecidos"}), 400

    nome = data.get("nome")
    referenciaPix = data.get("referenciaPix")
    email = data.get("email")
    senha = data.get("senha")

    # Validações básicas
    if not nome or len(nome.strip()) < 2:
        return jsonify({"erro": "Nome deve ter pelo menos 2 caracteres"}), 400

    if not referenciaPix or len(referenciaPix.strip()) < 1:
        return jsonify({"erro": "Referência PIX não pode estar vazia"}), 400

    if not email:
        return jsonify({"erro": "Email é obrigatório"}), 400

    if not senha or len(senha) < 6:
        return jsonify({"erro": "Senha deve ter pelo menos 6 caracteres"}), 400

    # Criar nova conta para o usuário
    nova_conta = Account.create() # Esse method cria uma conta com um endereço aleatório(sem relação com o Ganache)
    carteiraUsuario = nova_conta.address
    private_key_user = nova_conta.key.hex()

        # Armazenar a conta por email
        #contas_usuarios[email] = {
        #    'address': carteiraUsuario,
        #    'private_key': private_key_user
        #}

    # Salvando a conta por referenciaPix (IMPORTANTE: uso na realizaPagamento p/ busca de qual cliente irá fazer a transferência)
    contas_usuarios[referenciaPix] = {
        'address': carteiraUsuario,
        'private_key': private_key_user,
        'email': email
    }

    # Transferir alguns ETH para a nova conta
    transfer_nonce = w3.eth.get_transaction_count(admWallet)
    transfer_tx = {
        'to': carteiraUsuario,
        'value': w3.to_wei(0.1, 'ether'),
        'gas': 21000,
        'gasPrice': w3.eth.gas_price,
        'nonce': transfer_nonce,
        'chainId': w3.eth.chain_id
    }

    signed_transfer = w3.eth.account.sign_transaction(transfer_tx, private_key)
    w3.eth.send_raw_transaction(signed_transfer.raw_transaction)

    # Aguardar a transação de transferência
    time.sleep(2)

    nonce = w3.eth.get_transaction_count(carteiraUsuario)

    transaction = sistema_cliente.functions.registrarCliente(
            nome, referenciaPix, email, senha
        ).build_transaction(
            {
                "gasPrice": w3.eth.gas_price,
                "chainId": w3.eth.chain_id,
                "from": carteiraUsuario,
                "nonce": nonce,
            }
        )

    transaction_hash = sign_n_send(transaction, private_key_user)

    return jsonify({
            "status": "Usuário registrado com sucesso!",
            "carteira": carteiraUsuario,
            "transacao": receipt["transactionHash"].hex()
        })

# Mostra as infos do cliente:
@app.route("/mostraInfoCliente", methods=["GET"])
def mostraInfoCliente():
    address = request.args.get("carteira")

    if not address:
        return jsonify({"erro": "Parâmetro 'carteira' é obrigatório!"}), 400

    if not address.strip():
        return jsonify({"erro": "Endereço da carteira não pode estar vazio!"}), 400

    try:
        endereco = w3.to_checksum_address(address)
        print("Endereço cliente:", endereco)
    except ValueError:
        return jsonify({"erro": "Formato de endereço da carteira inválido!"}), 400

    print("Contrato usado:", sistema_cliente_address)

    sistemaCliente = w3.eth.contract(address=sistema_cliente_address, abi=sistema_cliente_abi)

    try:
        dados = sistemaCliente.functions.mostraInfoCliente(endereco).call()
        enderecoConta, nome, saldo, registrado, referenciaPix, email = dados

        # Converter saldo para ETH e depois para BRL
        saldo_eth = w3.from_wei(saldo, 'ether')

        # Buscar cotação atual do ETH em BRL
        try:
            cotacao_eth_brl = get_eth_to_brl()
            saldo_reais = float(saldo_eth) * cotacao_eth_brl
        except Exception as e:
            print(f"Erro ao buscar cotação: {e}")
            cotacao_eth_brl = None
            saldo_reais = None

        return jsonify({
            "nome": nome,
            "email": email,
            "referenciaPix": referenciaPix,
            "enderecoConta": enderecoConta,
            "saldo": {
                "wei": saldo,
                "eth": str(saldo_eth),
                "reais": round(saldo_reais, 2) if saldo_reais is not None else None
            },
            "cotacao_eth_brl": round(cotacao_eth_brl, 2) if cotacao_eth_brl is not None else None,
            "registrado": registrado
        })

    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar informações do cliente: {str(e)}"}), 500

@app.route("/adicionaSaldo", methods=["POST"])
def adicionaSaldo():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Dados JSON não fornecidos"}), 400

    endereco_cliente = data.get("carteira")
    valor_reais = data.get("valor_reais")

    # Validação básica
    if not endereco_cliente:
        return jsonify({"erro": "Endereço da carteira é obrigatório!"}), 400
    if not w3.is_address(endereco_cliente):
        return jsonify({"erro": "Endereço inválido!"}), 400

    try:
        valor_reais = float(valor_reais)
        if valor_reais <= 0:
            return jsonify({"erro": "Valor deve ser maior que zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"erro": "Valor inválido. Deve ser um número positivo."}), 400

    # Obter cotação atual do ETH em BRL usando função utilitária
    try:
        cotacao = get_eth_to_brl()
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar cotação: {str(e)}"}), 500

    # Converter BRL -> ETH -> WEI
    valor_eth = valor_reais / cotacao
    valor_wei = w3.to_wei(valor_eth, 'ether')

    endereco_cliente = w3.to_checksum_address(endereco_cliente)
    nonce = w3.eth.get_transaction_count(admWallet)

    # Construir a transação
    tx = sistema_cliente.functions.adicionarSaldo(endereco_cliente, valor_wei).build_transaction({
        "from": admWallet,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id
    })

    # Assinar e enviar
    receipt = sign_n_send(tx, private_key)

    return jsonify({
        "status": "Saldo adicionado com sucesso!",
        "tx_hash": receipt["transactionHash"].hex(),
        "valor_reais": valor_reais,
        "valor_eth": valor_eth,
        "valor_wei": valor_wei,
        "cotacao_eth_brl": cotacao
    })


@app.route("/realizaPagamento", methods=["POST"])
def realizaPagamento():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Dados JSON não fornecidos"}), 400

    # Validar campos obrigatórios
    required_fields = ['valor_reais', 'referenciaPix', 'comerciante']
    for field in required_fields:
        if field not in data:
            return jsonify({"erro": f"Campo '{field}' é obrigatório"}), 400

    valor_reais = data['valor_reais']
    referenciaPix = data['referenciaPix']
    comerciante_raw = data['comerciante']

    # Buscar endereço do cliente pela referência Pix
    endereco_cliente = sistema_cliente.functions.getEnderecoPorPix(referenciaPix).call()

    if not w3.is_address(endereco_cliente) or endereco_cliente == "0x0000000000000000000000000000000000000000":
        return jsonify({"erro": "Cliente não registrado com essa referência Pix"}), 400

    # Validar valor
    try:
        valor_reais = float(valor_reais)
        if valor_reais <= 0:
            return jsonify({"erro": "Valor deve ser maior que zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"erro": "Valor inválido. Deve ser um número positivo"}), 400

    # Obter cotação ETH -> BRL
    try:
        eth_brl = get_eth_to_brl()
    except:
        return jsonify({"erro": "Erro ao buscar cotação atual do ETH"}), 500

    valor_eth = valor_reais / eth_brl
    valor_wei = w3.to_wei(valor_eth, 'ether')

    # Validar endereço do comerciante
    try:
        comerciante = w3.to_checksum_address(comerciante_raw)
    except ValueError:
        return jsonify({"erro": "Endereço do comerciante inválido"}), 400

    print("Valor (ETH):", valor_eth)
    print("Valor (WEI):", valor_wei)

    nonce = w3.eth.get_transaction_count(endereco_cliente)

    new_transaction = contract.functions.realizaPagamentoCliente(
        valor_wei, referenciaPix, comerciante
    ).build_transaction({
        "from": endereco_cliente,
        "nonce": nonce,
        "gasPrice": w3.eth.gas_price,
        "value": int(valor_wei)
    })

    cliente_info = contas_usuarios.get(referenciaPix)
    if not cliente_info:
        return jsonify({"erro": "Cliente não encontrado no servidor"}), 400

    private_key_cliente = cliente_info['private_key']
    receipt = sign_n_send(new_transaction, private_key_cliente)

    return jsonify({
        "valor_reais": valor_reais,
        "valor_eth": round(valor_eth, 8),
        "valor_wei": int(valor_wei),
        "transaction_hash": receipt["transactionHash"].hex()
    })

# Verificar saldo do comerciante:
from decimal import Decimal, getcontext

getcontext().prec = 18  # Define precisão alta

@app.route("/saldoComerciante", methods=["GET"])
def getMerchantSaldo():
    saldo_wei = contract.functions.saldoComerciante(merchantWallet).call()
    saldo_eth = Decimal(w3.from_wei(saldo_wei, 'ether'))

    cotacao_eth_brl = Decimal('18000.00')
    saldo_brl = saldo_eth * cotacao_eth_brl

    # Formatar para string com 2 casas decimais, sem arredondar demais
    return jsonify({
        "saldo_wei": saldo_wei,
        "saldo_eth": format(saldo_eth, '.6f'),      # 6 casas decimais
        "saldo_reais": format(saldo_brl, '.2f')    # 2 casas decimais
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
# sql odeio esse negocio podre
