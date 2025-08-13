import os
from datetime import datetime
from decimal import Decimal, getcontext

from sqlalchemy import text
from eth_account import Account
from flask import Flask, jsonify, request
from flask import send_file
from flask.cli import load_dotenv
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from Backend.deploy_output import sistema_cliente_address, etherFlow_address, sistema_cliente_abi, etherFlow_abi
from Backend.utils import sign_n_send, listAllAccounts, get_eth_to_brl, qr_degrade
from Backend.my_blockchain import w3, admWallet, private_key, merchantWallet
from Backend.qr_service import QRCodeService

etherFlow = w3.eth.contract(address=etherFlow_address, abi=etherFlow_abi)
sistema_cliente = w3.eth.contract(address=sistema_cliente_address, abi=sistema_cliente_abi)

print(merchantWallet)

# listAllAccounts() -- Uso p/ Debug

# Criar um set para inserir as contas:
contas_usuarios = {}

DB_HOST = "switchyard.proxy.rlwy.net"
DB_PORT = 39347
DB_USER = "root"
DB_PASS = "nLLldXjrPdDgYwBpubKiqMhKgEqFdMXE"
DB_NAME = "railway"

db = SQLAlchemy()

class Config:
    # Para desenvolvimento local
    if os.environ.get('RAILWAY_ENVIRONMENT'): # Se estiver web
        # Configuração para Railway
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # Configuração local
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost/sistema_blockchain_cliente'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

def create_app():
    global w3

    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    db.init_app(app)

    # Inicializa conexão com Ganache usando variável de ambiente
    # ganache_url = os.environ.get("GANACHE_URL", "http://127.0.0.1:7545")
    # w3 = Web3(Web3.HTTPProvider(ganache_url))

    @app.before_request
    def check_ganache():
        if w3.is_connected():
            print("✅ Conectado com sucesso ao Ganache!")
            print("Conta padrão:", w3.eth.accounts[0])
        else:
            print("⚠️ Não conectado com Ganache!")

    @app.route("/test-db")
    def test_db():
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return "Conexão com banco OK!"
        except Exception as e:
            return f"Erro na conexão: {str(e)}"

    return app

app = create_app()

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    referenciaPix = db.Column(db.String(100), unique=True, nullable=False)
    carteira = db.Column(db.String(42), nullable=False)
    # private_key = db.Column(db.Text, nullable=False)

    # Relacionamento com transações
    transacoes = db.relationship('Transacao', backref='cliente', lazy=True)


class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor_pagamento = db.Column(db.Double, nullable=False)  # Valor em reais
    descricao = db.Column(db.String(255), nullable=True)  # Descrição opcional
    beneficiado = db.Column(db.String(100), nullable=False)  # Nome do beneficiado
    data_transacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hash_transacao = db.Column(db.String(66), nullable=False)  # Hash da transação blockchain

    # Chave estrangeira para o cliente
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)

    def __repr__(self):
        return f'<Transacao {self.id}: R${self.valor_pagamento} para {self.beneficiado}>'

def converter_reais_para_wei(valor_reais):
    """
    Converte valor em reais para wei automaticamente baseado na cotação atual

    Args:
        valor_reais (float): Valor em reais a ser convertido

    Returns:
        dict: Dicionário com valor_wei, valor_eth, cotacao_usada

    Raises:
        Exception: Se houver erro na conversão ou busca de cotação
    """
    try:
        # Buscar cotação atual
        cotacao_eth_brl = get_eth_to_brl()

        # Converter reais para ETH
        valor_eth = valor_reais / cotacao_eth_brl

        # Converter ETH para Wei
        valor_wei = w3.to_wei(valor_eth, 'ether')

        return {
            'valor_wei': int(valor_wei),
            'valor_eth': valor_eth,
            'cotacao_usada': cotacao_eth_brl,
            'valor_reais_original': valor_reais
        }

    except Exception as e:
        raise Exception(f"Erro na conversão automática: {str(e)}")


def converter_wei_para_reais(valor_wei):
    """
    Converte valor em wei para reais automaticamente baseado na cotação atual

    Args:
        valor_wei (int): Valor em wei a ser convertido

    Returns:
        dict: Dicionário com valor_reais, valor_eth, cotacao_usada

    Raises:
        Exception: Se houver erro na conversão ou busca de cotação
    """
    try:
        # Converter Wei para ETH
        valor_eth = w3.from_wei(valor_wei, 'ether')

        # Buscar cotação atual
        cotacao_eth_brl = get_eth_to_brl()

        # Converter ETH para reais
        valor_reais = float(valor_eth) * cotacao_eth_brl

        return {
            'valor_reais': valor_reais,
            'valor_eth': float(valor_eth),
            'cotacao_usada': cotacao_eth_brl,
            'valor_wei_original': valor_wei
        }

    except Exception as e:
        raise Exception(f"Erro na conversão automática: {str(e)}")



@app.route('/')
def run():
    return 'API funcionando com sucesso!'

"""""
@app.route('/test-db')
def test_db():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "Conexão com banco OK!"
    except Exception as e:
        return f"Erro na conexão: {str(e)}"
"""""

# Registrar um novo cliente:
@app.route("/registrarCliente", methods=["POST"])
def registro_cliente():
    data = request.get_json()

    if not data:
        return jsonify({"erro": "Dados JSON não fornecidos"}), 400

    nome = data.get("nome", "").strip()
    referenciaPix = data.get("referenciaPix", "").strip()
    email = data.get("email", "").strip()
    senha = data.get("senha", "").strip()

    print("Nome:", nome)
    print("Referencia Pix:", referenciaPix)
    print("Email:", email)
    print("Senha:", senha)

    if not nome or len(nome) < 2:
        return jsonify({"erro": "Nome deve ter pelo menos 2 caracteres"}), 400

    if not referenciaPix:
        return jsonify({"erro": "Referência PIX não pode estar vazia"}), 400

    if not email:
        return jsonify({"erro": "Email é obrigatório"}), 400

    if not senha or len(senha) < 6:
        return jsonify({"erro": "Senha deve ter pelo menos 6 caracteres"}), 400

    # Criar nova conta para o usuário
    nova_conta = Account.create()  # Esse method cria uma conta com um endereço aleatório(sem relação com o Ganache)
    carteiraUsuario = nova_conta.address
    private_key_user = nova_conta.key.hex()

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

    receipt = sign_n_send(transaction, private_key_user)

    # Adiciona saldo de R$10
    cotacao = get_eth_to_brl()
    valor_eth = 10.0 / cotacao
    valor_wei = w3.to_wei(valor_eth, 'ether')

    bonus_nonce = w3.eth.get_transaction_count(admWallet)
    bonus_tx = sistema_cliente.functions.adicionarSaldo(referenciaPix, valor_wei).build_transaction({
        "from": admWallet,
        "nonce": bonus_nonce,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id
    })

    bonus_receipt = sign_n_send(bonus_tx, private_key)

    novoCliente = Cliente(nome=nome,
                          referenciaPix=referenciaPix,
                          email=email,
                          senha=senha,
                          carteira=carteiraUsuario)
                          # private_key=private_key_user)

    db.session.add(novoCliente)
    db.session.commit()

    return jsonify({
        "status": "Usuário registrado com sucesso e saldo de R$10,00 adicionado!",
        "carteira": carteiraUsuario,
        "tx_registro": receipt["transactionHash"].hex(),
        "tx_bonus": bonus_receipt["transactionHash"].hex()
    })


# Login de usuário:
@app.route("/loginClient", methods=["POST"])
def loginCliente():
    data = request.get_json()
    print("JSON parseado:", data)

    email = data.get("email", "").strip()
    senha = data.get("senha", "").strip()

    if not email or not senha:
        return jsonify({"erro": "Email e senha são obrigatórios!"}), 400

    try:
        # Chamada ao contrato para autenticar cliente
        autenticado, carteira = sistema_cliente.functions.autenticarCliente(email, senha).call()

        if not autenticado:
            return jsonify({"erro": "Credenciais inválidas!"}), 401

        carteira_checksum = w3.to_checksum_address(carteira)

        # Verifica se o cliente está registrado localmente (ou seja, foi registrado no dicionário `contas_usuarios`)
        cliente_info = None
        for referenciaPix, info in contas_usuarios.items():
            if info['email'] == email and w3.to_checksum_address(info['address']) == carteira_checksum:
                cliente_info = info
                break

        if not cliente_info:
            return jsonify({"erro": "Endereço da carteira não corresponde ou cliente não está registrado localmente"}), 401

        return jsonify({
            "status": "Login bem-sucedido!",
            "carteira": carteira_checksum,
            "email": email
        })

    except Exception as e:
        print("Erro ao autenticar:", str(e))
        return jsonify({"erro": f"Erro interno ao tentar login: {str(e)}"}), 500


""" debug
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
        
"""

""" Usar o AppState
@app.route("/adicionaSaldo", methods=["POST"])
def adicionaSaldo():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados JSON não fornecidos"}), 400

        referenciaPix = data.get("referenciaPix")
        valor_reais = data.get("valor_reais")

        if not referenciaPix:
            return jsonify({"erro": "Referencia Pix não fornecida"}), 400

        try:
            valor_reais = float(valor_reais)
            if valor_reais <= 0:
                return jsonify({"erro": "Valor deve ser maior que zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "Valor inválido. Deve ser um número positivo."}), 400

        try:
            cotacao = get_eth_to_brl()
        except Exception as e:
            return jsonify({"erro": f"Erro ao buscar cotação: {str(e)}"}), 500

        valor_eth = valor_reais / cotacao
        valor_wei = w3.to_wei(valor_eth, 'ether')

        nonce = w3.eth.get_transaction_count(admWallet)
        tx = sistema_cliente.functions.adicionarSaldo(referenciaPix, valor_wei).build_transaction({
            "from": admWallet,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id
        })

        receipt = sign_n_send(tx, private_key)

        return jsonify({
            "status": "Saldo adicionado com sucesso!",
            "tx_hash": receipt["transactionHash"].hex(),
            "valor_reais": valor_reais,
            "valor_eth": valor_eth,
            "valor_wei": valor_wei,
            "cotacao_eth_brl": cotacao
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500
        
"""

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
    descricao = data.get('descricao', '')  # Descrição opcional

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

    new_transaction = etherFlow.functions.realizaPagamentoCliente(
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

    # REGISTRAR A TRANSAÇÃO NO BANCO DE DADOS
    try:
        # Buscar o cliente no banco de dados
        clientes = Cliente.query.filter_by(referenciaPix=referenciaPix).first()
        if not clientes:
            return jsonify({"erro": "Cliente não encontrado no banco de dados"}), 400

        # Criar nova transação
        nova_transacao = Transacao(
            valor_pagamento=valor_reais,
            descricao=descricao if descricao else None,
            beneficiado="Comerciante",  # Por enquanto é constante
            hash_transacao=receipt["transactionHash"].hex(),
            cliente_id=clientes.id
        )

        # Salvar no banco
        db.session.add(nova_transacao)
        db.session.commit()

        print(f"Transação registrada no BD: ID {nova_transacao.id}")

    except Exception as e:
        print(f"Erro ao registrar transação no BD: {str(e)}")
        # Não interrompe o fluxo, pois a transação blockchain já foi realizada
        db.session.rollback()

    return jsonify({
        "valor_reais": valor_reais,
        "valor_eth": round(valor_eth, 8),
        "valor_wei": int(valor_wei),
        "transaction_hash": receipt["transactionHash"].hex(),
        "descricao": descricao,
        "beneficiado": "Comerciante"
    })

# Verificar saldo do comerciante:

getcontext().prec = 18  # Define precisão alta

@app.route("/transferirParaCliente", methods=["POST"])
def transferirParaCliente():
    """Realiza transferência entre clientes usando referência PIX"""
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Dados JSON não fornecidos"}), 400

    # Validar campos obrigatórios
    required_fields = ['valor_reais', 'referenciaPix_origem', 'referenciaPix_destino']
    for field in required_fields:
        if field not in data:
            return jsonify({"erro": f"Campo '{field}' é obrigatório"}), 400

    valor_reais = data['valor_reais']
    referencia_origem = data['referenciaPix_origem']
    referencia_destino = data['referenciaPix_destino']
    descricao = data.get('descricao', 'Transferência entre clientes')

    # Verificar se não é auto-transferência
    if referencia_origem == referencia_destino:
        return jsonify({"erro": "Não é possível transferir para si mesmo"}), 400

    # Validar valor
    try:
        valor_reais = float(valor_reais)
        if valor_reais <= 0:
            return jsonify({"erro": "Valor deve ser maior que zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"erro": "Valor inválido. Deve ser um número positivo"}), 400

    # Buscar endereços dos clientes
    try:
        endereco_origem = sistema_cliente.functions.getEnderecoPorPix(referencia_origem).call()
        endereco_destino = sistema_cliente.functions.getEnderecoPorPix(referencia_destino).call()

        if endereco_origem == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Cliente remetente não encontrado"}), 400

        if endereco_destino == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Cliente destinatário não encontrado"}), 400

    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar clientes: {str(e)}"}), 500

    # Obter cotação e converter valor
    try:
        cotacao_eth_brl = get_eth_to_brl()
        valor_eth = valor_reais / cotacao_eth_brl
        valor_wei = w3.to_wei(valor_eth, 'ether')
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar cotação: {str(e)}"}), 500

    # Verificar saldo do remetente
    try:
        saldo_origem = sistema_cliente.functions.consultarSaldo(referencia_origem).call()
        if saldo_origem < valor_wei:
            saldo_reais = (w3.from_wei(saldo_origem, 'ether') * cotacao_eth_brl)
            return jsonify({
                "erro": "Saldo insuficiente",
                "saldo_atual_reais": round(saldo_reais, 2)
            }), 400
    except Exception as e:
        return jsonify({"erro": f"Erro ao verificar saldo: {str(e)}"}), 500

    # Buscar chave privada do remetente
    cliente_origem_info = contas_usuarios.get(referencia_origem)
    if not cliente_origem_info:
        return jsonify({"erro": "Dados do cliente remetente não encontrados no servidor"}), 400

    private_key_origem = cliente_origem_info['private_key']

    try:
        # Executar transferência no blockchain
        nonce = w3.eth.get_transaction_count(endereco_origem)

        # Usar função de transferência do contrato sistema_cliente
        transaction = sistema_cliente.functions.transferirSaldo(
            referencia_origem,
            referencia_destino,
            valor_wei
        ).build_transaction({
            "from": endereco_origem,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id
        })

        receipt = sign_n_send(transaction, private_key_origem)

        # Registrar transação no banco de dados para o remetente
        try:
            cliente_origem = Cliente.query.filter_by(referenciaPix=referencia_origem).first()
            cliente_destino = Cliente.query.filter_by(referenciaPix=referencia_destino).first()

            if cliente_origem and cliente_destino:
                # Transação de saída para o remetente
                transacao_saida = Transacao(
                    valor_pagamento=-valor_reais,  # Negativo para indicar saída
                    descricao=f"Transferência para {cliente_destino.nome}: {descricao}",
                    beneficiado=cliente_destino.nome,
                    hash_transacao=receipt["transactionHash"].hex(),
                    cliente_id=cliente_origem.id
                )

                # Transação de entrada para o destinatário
                transacao_entrada = Transacao(
                    valor_pagamento=valor_reais,  # Positivo para indicar entrada
                    descricao=f"Recebimento de {cliente_origem.nome}: {descricao}",
                    beneficiado=cliente_origem.nome,
                    hash_transacao=receipt["transactionHash"].hex(),
                    cliente_id=cliente_destino.id
                )

                db.session.add(transacao_saida)
                db.session.add(transacao_entrada)
                db.session.commit()

        except Exception as e:
            print(f"Erro ao registrar transação no BD: {str(e)}")
            db.session.rollback()

        return jsonify({
            "status": "Transferência realizada com sucesso!",
            "valor_reais": valor_reais,
            "valor_eth": round(valor_eth, 8),
            "referencia_origem": referencia_origem,
            "referencia_destino": referencia_destino,
            "transaction_hash": receipt["transactionHash"].hex(),
            "cotacao_eth_brl": round(cotacao_eth_brl, 2),
            "descricao": descricao
        })

    except Exception as e:
        return jsonify({"erro": f"Erro ao executar transferência: {str(e)}"}), 500

@app.route("/saldoComerciante", methods=["GET"])
def getMerchantBalance():
    saldo_wei = etherFlow.functions.saldoComerciante(merchantWallet).call()
    saldo_eth = Decimal(w3.from_wei(saldo_wei, 'ether'))

    cotacao_eth_brl = Decimal('18000.00')
    saldo_brl = saldo_eth * cotacao_eth_brl

    # Formatar para string com 2 casas decimais, sem arredondar demais
    return jsonify({
        "saldo_wei": saldo_wei,
        "saldo_eth": format(saldo_eth, '.6f'),  # 6 casas decimais
        "saldo_reais": format(saldo_brl, '.2f')  # 2 casas decimais
    })

# Nova rota para listar transações de um cliente
@app.route("/transacoesCliente", methods=["GET"])
def listarTransacoesCliente():
    referencia_pix = request.args.get("referenciaPix")

    if not referencia_pix:
        return jsonify({"erro": "Parâmetro 'referenciaPix' é obrigatório!"}), 400

    try:
        # Buscar cliente
        cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
        if not cliente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        # Buscar transações do cliente
        transacoes = Transacao.query.filter_by(cliente_id=cliente.id).order_by(Transacao.data_transacao.desc()).all()

        transacoes_list = []
        for transacao in transacoes:
            transacoes_list.append({
                "id": transacao.id,
                "valor_pagamento": str(transacao.valor_pagamento),
                "descricao": transacao.descricao,
                "beneficiado": transacao.beneficiado,
                "data_transacao": transacao.data_transacao.isoformat(),
                "hash_transacao": transacao.hash_transacao
            })

        return jsonify({
            "cliente": cliente.nome,
            "total_transacoes": len(transacoes_list),
            "transacoes": transacoes_list
        })

    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar transações: {str(e)}"}), 500

# Doação para ONG:
@app.route("/donate", methods=["POST"])
def donate():
    data = request.get_json()

    if not data:
        return jsonify({"erro": "Nenhum dado JSON recebido"}), 400

    valor_reais = data.get("valorReais")
    referencia_pix = data.get("referenciaPix", "").strip()

    if valor_reais is None or referencia_pix == "":
        return jsonify({"erro": "Campos obrigatórios: valorReais e referenciaPix"}), 400

    try:
        valor_reais = float(valor_reais)
        if valor_reais <= 0:
            return jsonify({"erro": "O valor da doação deve ser maior que zero"}), 400
    except ValueError:
        return jsonify({"erro": "valorReais deve ser um número"}), 400

    try:
        # Buscar endereço do cliente pela referência Pix
        endereco_cliente = sistema_cliente.functions.getEnderecoPorPix(referencia_pix).call()
        if not w3.is_address(endereco_cliente) or endereco_cliente == w3.to_checksum_address("0x0000000000000000000000000000000000000000"):
            return jsonify({"erro": "Cliente não registrado com essa referência Pix"}), 400

        cliente_info = contas_usuarios.get(referencia_pix)
        if not cliente_info:
            return jsonify({"erro": "Cliente não encontrado no servidor"}), 400

        # Conversão BRL → ETH → WEI
        cotacao = get_eth_to_brl()
        valor_eth = valor_reais / cotacao
        valor_wei = w3.to_wei(valor_eth, 'ether')

        # Criar transação (saldo já será verificado no contrato)
        nonce = w3.eth.get_transaction_count(endereco_cliente)
        tx = etherFlow.functions.doacaoDireta().build_transaction({
            "from": endereco_cliente,
            "value": int(valor_wei),
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id
        })

        # Assinar e enviar
        signed_tx = sign_n_send(tx, cliente_info['private_key'])

        # Registrar no banco
        try:
            cliente_db = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if cliente_db:
                nova_transacao = Transacao(
                    valor_pagamento=valor_reais,
                    descricao="Doação para ONG",
                    beneficiado="ONG - Conta: 0x5435f2DB7d42635225FbE2D9B356B693e1F53D2F",
                    hash_transacao=signed_tx["transactionHash"].hex(),
                    cliente_id=cliente_db.id
                )
                db.session.add(nova_transacao)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao registrar no BD: {str(e)}")

        return jsonify({
            "status": "Doação realizada com sucesso!",
            "valor_wei": int(valor_wei),
            "valor_eth": str(valor_eth),
            "valor_brl": round(valor_reais, 2),
            "cotacao": cotacao,
            "transaction_hash": signed_tx["transactionHash"].hex(),
            "gas_usado": signed_tx.get("gasUsed", "N/A"),
            "endereco_doador": endereco_cliente,
            "endereco_ong": "0x5435f2DB7d42635225FbE2D9B356B693e1F53D2F"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao processar a doação: {str(e)}"}), 500

"""
                                Implantação dos QRCodes:
                                Registro: Site
                                Comerciante: Transação Pix
"""

# Inicializar o serviço de QR codes
qr_service = QRCodeService()

@app.route("/qrcode-registro")
def criar_qrcode_registro():
    """Gera QR code com degradê para registro"""
    url = "https://cryp2real.flutterflow.app/register"
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Gerar apenas o QR com degradê
    caminho_relativo = qr_service.gerar_qr_degrade(url)
    caminho_absoluto = qr_service.obter_caminho_absoluto(caminho_relativo, base_dir)

    print(f"Enviando arquivo: {caminho_absoluto}")
    return send_file(caminho_absoluto, mimetype='image/png')

@app.route("/qrcode-comerciante")
def criar_qrcode_comerciante():
    """Gera QR code padrão para chave do comerciante"""
    chave_comerciante = "0x5435f2DB7d42635225FbE2D9B356B693e1F53D2F"
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Gerar QR padrão para a chave do comerciante
    caminho_relativo = qr_service.gerar_qr_padrao(chave_comerciante, "comerciante_chave.png")
    caminho_absoluto = qr_service.obter_caminho_absoluto(caminho_relativo, base_dir)

    print(f"Enviando QR da chave do comerciante: {caminho_absoluto}")
    return send_file(caminho_absoluto, mimetype='image/png')

@app.route("/gerar-qrcodes")
def gerar_qrcodes():
    """Gera os dois QR codes e confirma que foram salvos"""
    url_registro = "https://cryp2real.flutterflow.app"
    chave_comerciante = "0x5435f2DB7d42635225FbE2D9B356B693e1F53D2F"

    # Gerar ambos os QR codes
    caminhos = qr_service.gerar_qr_codes_completos(url_registro, chave_comerciante)

    return {
        "status": "sucesso",
        "message": "QR codes gerados com sucesso!",
        "arquivos": {
            "registro": caminhos['registro'],
            "comerciante": caminhos['comerciante']
        }
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)