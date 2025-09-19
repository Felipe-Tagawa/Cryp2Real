import hashlib
import io
import os
import secrets
import traceback
from datetime import datetime, timezone
from dotenv import load_dotenv

from flask import Flask, jsonify, request, session, Response
from flask import send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from matplotlib import pyplot as plt
from sqlalchemy import text

from Backend.my_blockchain import w3, etherFlow, sistema_cliente
from Backend.qr_service import QRCodeService
from Backend.utils import sign_n_send, get_eth_to_brl, getGanacheAccount

# listAllAccounts() -- Uso p/ Debug

load_dotenv()

db = SQLAlchemy()

class Config:
    # Para desenvolvimento local
    if os.environ.get('RAILWAY_ENVIRONMENT'): # Se estiver web
        # Configuração para Railway
        SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI',"mysql+pymysql://root:nLLldXjrPdDgYwBpubKiqMhKgEqFdMXE@switchyard.proxy.rlwy.net:39347/sistema_blockchain_cliente")

        print("🚀 Conectando ao banco de produção (Railway)")
    else:
        # Configuração local
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://root:{os.getenv('BDPASS')}@localhost/sistema_blockchain_cliente"
        print("Conectado ao Banco Local")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

db.init_app(app)

app.secret_key = secrets.token_hex(16)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    referenciaPix = db.Column(db.String(100), unique=True, nullable=False)
    carteira = db.Column(db.String(42), nullable=False)
    saldo_ether = db.Column(db.Float, default=0.0)
    saldo_reais = db.Column(db.Float, default=0.0)
    private_key = db.Column(db.Text, nullable=False)

    # Relacionamento com transações
    transacoes = db.relationship('Transacao', backref='cliente', lazy=True)


class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor_pagamento = db.Column(db.Double, nullable=False)  # Valor em reais
    descricao = db.Column(db.String(255), nullable=True)  # Descrição opcional
    beneficiado = db.Column(db.String(100), nullable=False)  # Nome do beneficiado
    data_transacao = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    hash_transacao = db.Column(db.String(66), nullable=False)  # Hash da transação blockchain
    tipo_transacao = db.Column(db.String(100), nullable=False)  # eth_direto ou sem_taxas

    # Chave estrangeira para o cliente
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)

    def __repr__(self):
        return f'<Transacao {self.id}: R${self.valor_pagamento} para {self.beneficiado}>'

@app.route('/')
def run():
    return 'API funcionando com sucesso!'

@app.route("/test-db")
def test_db():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "Conexão com banco OK!"
    except Exception as e:
        return f"Erro na conexão: {str(e)}"

@app.route("/test-ganache")
def test_ganache():
    try:
        if w3.is_connected():
            return {
                "status": "conectado",
                "conta_padrao": w3.eth.accounts[0],
                "block_number": w3.eth.block_number
            }
        else:
            return {"status": "desconectado"}, 500
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}, 500

# Registrar um novo cliente:

@app.route("/registrarCliente", methods=["POST"])
def registro_cliente():
    try:
        data = request.get_json()
        nome = data.get("nome", "").strip()
        referenciaPix = data.get("referenciaPix", "").strip()
        email = data.get("email", "").strip()
        senha = data.get("senha", "").strip()
        # Insira aqui o saldo do cliente - saldo_eth
        senhaHash = hashlib.sha256(senha.encode('utf-8')).hexdigest()


        if not nome or len(nome) < 2:
            return jsonify({"erro": "Nome deve ter pelo menos 2 caracteres"}), 400
        if not referenciaPix:
            return jsonify({"erro": "Referência PIX não pode estar vazia"}), 400
        if not email:
            return jsonify({"erro": "Email é obrigatório"}), 400
        if not senha or len(senha) < 2:
            return jsonify({"erro": "Senha deve ter pelo menos 2 caracteres"}), 400


        endereco_existente = sistema_cliente.functions.getEnderecoPorPix(referenciaPix).call()
        if endereco_existente != "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": f"Referência PIX '{referenciaPix}' já está cadastrada no blockchain!"}), 400


        existing_client = Cliente.query.filter_by(referenciaPix=referenciaPix).first()
        if existing_client:
            return jsonify({"erro": f"Referência PIX '{referenciaPix}' já está cadastrada no banco!"}), 400


        userAddress, privateKeyUser = getGanacheAccount()
        transaction = sistema_cliente.functions.registrarCliente(
            nome, referenciaPix, email, senha
            ).build_transaction({
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
            "from": userAddress,
            "nonce": w3.eth.get_transaction_count(userAddress),
            "gas": 500000,
            })
        receipt = sign_n_send(transaction, privateKeyUser)


        newClient = Cliente(
            nome=nome,
            referenciaPix=referenciaPix,
            email=email,
            senha=senhaHash,
            carteira=userAddress,
            saldo_ether=float(w3.from_wei(w3.eth.get_balance(userAddress), 'ether')),
            private_key=privateKeyUser
        )

        db.session.add(newClient)
        db.session.commit()

        # Salva na sessão para já estar logado
        session['email'] = newClient.email
        session['carteira'] = newClient.carteira

        return jsonify({
            "status": "Usuário registrado com sucesso!",
            "carteira": userAddress,
            "saldo_inicial": f"{w3.from_wei(w3.eth.get_balance(userAddress), 'ether')} ETH",
            "tx_registro": receipt["transactionHash"].hex(),
            "referenciaPix": referenciaPix,
            "nome": nome,
            "email": email
            }), 200
    except Exception as e:
        db.session.rollback()
        print("❌ Erro em /registrarCliente:", str(e))
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao registrar cliente: {str(e)}"}), 500


# Login de usuário:
@app.route("/loginClient", methods=["POST"])
def loginCliente():
    data = request.get_json()
    email = data.get("email", "").strip()
    senha = data.get("senha", "").strip()
    if not email or not senha:
        return jsonify({"erro": "Email e senha são obrigatórios!"}), 400
    try:
        autenticado, carteira = sistema_cliente.functions.autenticarCliente(email, senha).call()
        if not autenticado:
            return jsonify({"erro": "Credenciais inválidas!"}), 401
        carteira_checksum = w3.to_checksum_address(carteira)
        cliente = Cliente.query.filter_by(email=email).first()
        if not cliente:
            return jsonify({"erro": "Cliente não encontrado no banco"}), 404
        if w3.to_checksum_address(cliente.carteira) != carteira_checksum:
            return jsonify({"erro": "Carteira no banco não confere com a blockchain"}), 400

        # 🔹 Salvar na sessão
        session['cliente_id'] = cliente.id
        session['email'] = cliente.email
        session['carteira'] = cliente.carteira

        return jsonify({
            "status": "Login bem-sucedido!",
            "carteira": carteira_checksum,
            "email": cliente.email,
            "nome": cliente.nome,
            "referenciaPix": cliente.referenciaPix
        })
    except Exception as e:
        return jsonify({"erro": f"Erro interno ao tentar login: {str(e)}"}), 500


# Mostra as infos do cliente:
@app.route("/mostraInfoCliente", methods=["GET"])
def mostraInfoCliente():
    referencia_pix = request.args.get("referenciaPix")

    if not referencia_pix:
        return jsonify({"erro": "Parâmetro 'referenciaPix' é obrigatório!"}), 400

    if not referencia_pix.strip():
        return jsonify({"erro": "referenciaPix não pode estar vazio!"}), 400

    try:
        # Buscar o endereço associado à referência Pix
        endereco = sistema_cliente.functions.getEnderecoPorPix(referencia_pix).call()

        if not w3.is_address(endereco) or endereco == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Nenhum cliente encontrado para essa referenciaPix"}), 404

        endereco = w3.to_checksum_address(endereco)
        print("Endereço cliente:", endereco)

        # Chama o contrato para pegar as informações completas
        dados = sistema_cliente.functions.mostraInfoCliente(endereco).call()
        carteiraContrato, nome, saldo, registrado, referenciaPix, email = dados

        return jsonify({
            "nome": nome,
            "email": email,
            "referenciaPix": referenciaPix,
            "carteira": carteiraContrato,
            "registrado": registrado
        })

    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar informações do cliente: {str(e)}"}), 500


@app.route("/getName", methods=["GET"])
def getName():
    referencia_pix = request.args.get("referenciaPix")

    if not referencia_pix:
        return jsonify({"erro": "referenciaPix obrigatória na query string"}), 400

    try:
        # Tenta buscar o cliente no banco de dados
        cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
        if not cliente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        # Tenta buscar o nome no contrato Solidity
        try:
            nome_cliente = etherFlow.functions.getNomeCliente(referencia_pix).call()
        except Exception as e:
            nome_cliente = None
            print(f"Erro ao buscar nome no contrato: {e}")

        return jsonify({
            "status": "sucesso",
            "cliente_id": cliente.id,
            "referenciaPix": cliente.referenciaPix,
            "nome": nome_cliente if nome_cliente else cliente.nome  # fallback para banco
        }), 200

    except Exception as e:
        # Qualquer outro erro inesperado
        return jsonify({"erro": f"Erro interno ao buscar cliente: {str(e)}"}), 500


@app.route("/getBalance", methods=["GET"])
def getBalance():
    try:

        referencia_pix = request.args.get('referenciaPix')

        if referencia_pix:
            cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if not cliente:
                return jsonify({"erro": "Cliente não encontrado"}), 404
        else:
            cliente_id = session.get("cliente_id")
            if not cliente_id:
                return jsonify({"erro": "referenciaPix obrigatória na query string ou sessão válida"}), 400
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return jsonify({"erro": "Cliente da sessão não encontrado"}), 404

        address = w3.to_checksum_address(cliente.carteira)

        # Saldo real da carteira ETH
        saldo_wei = w3.eth.get_balance(address)
        saldo_eth = w3.from_wei(saldo_wei, "ether")

        # Saldo interno no contrato
        try:
            saldo_interno_wei = etherFlow.functions.saldoCliente().call({'from': address})
            saldo_interno_eth = w3.from_wei(saldo_interno_wei, "ether")
        except Exception as e:
            saldo_interno_eth = None
            print(f"Erro ao buscar saldo interno: {e}")

        # CONVERSÃO SIMPLIFICADA: 1 ETH = 1 BRL
        cotacao_eth_brl = 1.0

        saldo_brl = float(saldo_eth) * cotacao_eth_brl  # Sempre 1:1
        saldo_interno_brl = float(saldo_interno_eth) * cotacao_eth_brl if saldo_interno_eth else None

        return jsonify({
            "status": "sucesso",
            "cliente_id": cliente.id,
            "nome": cliente.nome,
            "email": cliente.email,
            "referenciaPix": cliente.referenciaPix,
            "carteira": address,

            # Saldos principais (agora iguais!)
            "balance_eth": float(saldo_eth),
            "balance_brl": round(saldo_brl, 2),
            "balance_interno_eth": float(saldo_interno_eth) if saldo_interno_eth else None,
            "balance_interno_brl": round(saldo_interno_brl, 2) if saldo_interno_brl else None,

            # Info do sistema
            "cotacao_eth_brl": cotacao_eth_brl,  # Sempre 1.0
            "fonte_dados": "ganache_blockchain + etherFlow (1ETH = 1BRL)",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

        }), 200

    except Exception as e:
        return jsonify({"erro": f"Erro interno ao buscar saldo: {str(e)}"}), 500


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

    cliente_db = Cliente.query.filter_by(referenciaPix=referenciaPix).first()
    if not cliente_db:
        return jsonify({"erro": "Cliente não encontrado no banco de dados"}), 400
    private_key_cliente = cliente_db.private_key

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
            beneficiado="Comerciante",
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

@app.route("/transferirEntreUsers", methods=["POST"])
def transferirEntreUsers():
    global valor, valor_eth, valor_reais, eth_brl
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Dados JSON não fornecidos"}), 400

    # Validar campos obrigatórios
    required_fields = ['referencia_origem', 'referencia_destino', 'tipo_transferencia']
    for field in required_fields:
        if field not in data:
            return jsonify({"erro": f"Campo '{field}' é obrigatório"}), 400

    referencia_origem = data['referencia_origem']
    referencia_destino = data['referencia_destino']
    tipo_transferencia = data['tipo_transferencia']  # 'saldo_interno', 'eth_direto', 'sem_taxas'
    descricao = data.get('descricao', '')

    # Verificar auto-transferência
    if referencia_origem == referencia_destino:
        return jsonify({"erro": "Não é possível transferir para si mesmo"}), 400

    # Buscar endereços
    endereco_origem = sistema_cliente.functions.getEnderecoPorPix(referencia_origem).call()
    endereco_destino = sistema_cliente.functions.getEnderecoPorPix(referencia_destino).call()

    if not w3.is_address(endereco_origem) or endereco_origem == "0x0000000000000000000000000000000000000000":
        return jsonify({"erro": "Usuário de origem não registrado"}), 400

    if not w3.is_address(endereco_destino) or endereco_destino == "0x0000000000000000000000000000000000000000":
        return jsonify({"erro": "Usuário de destino não registrado"}), 400

    # Buscar dados do cliente origem
    cliente_origem = Cliente.query.filter_by(referenciaPix=referencia_origem).first()
    if not cliente_origem:
        return jsonify({"erro": "Cliente origem não encontrado no banco de dados"}), 400

    private_key_origem = cliente_origem.private_key
    nonce = w3.eth.get_transaction_count(endereco_origem)

    try:
        # OPÇÃO 1: Transferência usando saldo interno do contrato
        if tipo_transferencia == 'saldo_interno':
            if 'valor' not in data:
                return jsonify({"erro": "Campo 'valor' é obrigatório para transferência por saldo interno"}), 400

            valor = float(data['valor'])
            valor_wei = w3.to_wei(valor, 'ether')

            # Verificar saldo interno
            saldo_interno = etherFlow.functions.consultarSaldoInterno(endereco_origem).call()
            if saldo_interno < valor_wei:
                return jsonify({
                    "erro": "Saldo interno insuficiente",
                    "saldo_interno_eth": float(w3.from_wei(saldo_interno, 'ether')),
                    "valor_solicitado": valor
                }), 400

            transaction = etherFlow.functions.transferirParaUsuario(
                valor_wei,
                referencia_origem,  # Usar como referência da transação
                endereco_destino
            ).build_transaction({
                "from": endereco_origem,
                "nonce": nonce,
                "gasPrice": w3.eth.gas_price,
            })

        # OPÇÃO 2: Transferência ETH direto com taxas
        elif tipo_transferencia == 'eth_direto':
            if 'valor_eth' not in data:
                return jsonify({"erro": "Campo 'valor_eth' é obrigatório para transferência ETH direto"}), 400

            valor_eth = float(data['valor_eth'])
            valor_wei = w3.to_wei(valor_eth, 'ether')

            # Verificar saldo ETH
            saldo_eth = w3.eth.get_balance(endereco_origem)
            gas_estimate = etherFlow.functions.transferirETHDireto(
                referencia_origem, endereco_destino
            ).estimate_gas({"from": endereco_origem, "value": valor_wei})

            gas_cost = gas_estimate * w3.eth.gas_price
            total_necessario = valor_wei + gas_cost

            if saldo_eth < total_necessario:
                return jsonify({
                    "erro": "Saldo ETH insuficiente",
                    "saldo_atual_eth": float(w3.from_wei(saldo_eth, 'ether')),
                    "valor_transferencia": valor_eth,
                    "gas_estimado_eth": float(w3.from_wei(gas_cost, 'ether')),
                    "total_necessario_eth": float(w3.from_wei(total_necessario, 'ether'))
                }), 400

            transaction = etherFlow.functions.transferirETHDireto(
                referencia_origem,
                endereco_destino
            ).build_transaction({
                "from": endereco_origem,
                "nonce": nonce,
                "gasPrice": w3.eth.gas_price,
                "value": valor_wei
            })

        # OPÇÃO 3: Transferência sem taxas (P2P puro)
        elif tipo_transferencia == 'sem_taxas':
            if 'valor_eth' not in data:
                return jsonify({"erro": "Campo 'valor_eth' é obrigatório para transferência sem taxas"}), 400

            valor_eth = float(data['valor_eth'])
            valor_wei = w3.to_wei(valor_eth, 'ether')

            # Verificar saldo ETH
            saldo_eth = w3.eth.get_balance(endereco_origem)
            gas_estimate = etherFlow.functions.transferenciaSemTaxas(
                referencia_origem, endereco_destino
            ).estimate_gas({"from": endereco_origem, "value": valor_wei})

            gas_cost = gas_estimate * w3.eth.gas_price
            total_necessario = valor_wei + gas_cost

            if saldo_eth < total_necessario:
                return jsonify({
                    "erro": "Saldo ETH insuficiente",
                    "saldo_atual_eth": float(w3.from_wei(saldo_eth, 'ether')),
                    "valor_transferencia": valor_eth,
                    "gas_estimado_eth": float(w3.from_wei(gas_cost, 'ether')),
                    "total_necessario_eth": float(w3.from_wei(total_necessario, 'ether'))
                }), 400

            transaction = etherFlow.functions.transferenciaSemTaxas(
                referencia_origem,
                endereco_destino
            ).build_transaction({
                "from": endereco_origem,
                "nonce": nonce,
                "gasPrice": w3.eth.gas_price,
                "value": valor_wei
            })

        else:
            return jsonify(
                {"erro": "Tipo de transferência inválido. Use: 'saldo_interno', 'eth_direto', ou 'sem_taxas'"}), 400

        # Assinar e enviar transação
        receipt = sign_n_send(transaction, private_key_origem)

        # Registrar no banco de dados
        try:
            cliente_origem_db = Cliente.query.filter_by(referenciaPix=referencia_origem).first()
            cliente_destino_db = Cliente.query.filter_by(referenciaPix=referencia_destino).first()

            # Obter cotação para registro histórico
            try:
                eth_brl = get_eth_to_brl()
                if tipo_transferencia == 'saldo_interno':
                    valor_reais = valor * eth_brl
                else:
                    valor_reais = valor_eth * eth_brl
            except:
                valor_reais = None

            # Registro de saída para o remetente
            desc_saida = f"Transferência {tipo_transferencia} para {referencia_destino}"
            if descricao:
                desc_saida += f": {descricao}"

            transacao_saida = Transacao(
                valor_pagamento=valor_reais if valor_reais else (
                    valor if tipo_transferencia == 'saldo_interno' else valor_eth),
                descricao=desc_saida,
                beneficiado=f"Usuário {referencia_destino}",
                hash_transacao=receipt["transactionHash"].hex(),
                cliente_id=cliente_origem_db.id,
                tipo_transacao="SAIDA"
            )
            db.session.add(transacao_saida)

            # Registro de entrada para o destinatário (se estiver no sistema)
            if cliente_destino_db:
                desc_entrada = f"Recebido {tipo_transferencia} de {referencia_origem}"
                if descricao:
                    desc_entrada += f": {descricao}"

                transacao_entrada = Transacao(
                    valor_pagamento=valor_reais if valor_reais else (
                        valor if tipo_transferencia == 'saldo_interno' else valor_eth),
                    descricao=desc_entrada,
                    beneficiado=f"Usuário {referencia_origem}",
                    hash_transacao=receipt["transactionHash"].hex(),
                    cliente_id=cliente_destino_db.id,
                    tipo_transacao="ENTRADA"
                )
                db.session.add(transacao_entrada)

            db.session.commit()

        except Exception as e:
            print(f"Erro ao registrar no BD: {str(e)}")
            db.session.rollback()

        # Preparar resposta
        response = {
            "sucesso": True,
            "tipo_transferencia": tipo_transferencia,
            "transaction_hash": receipt["transactionHash"].hex(),
            "gas_usado": receipt["gasUsed"],
            "custo_gas_eth": float(w3.from_wei(receipt["gasUsed"] * w3.eth.gas_price, 'ether')),
            "origem": {
                "referencia": referencia_origem,
                "endereco": endereco_origem,
            },
            "destino": {
                "referencia": referencia_destino,
                "endereco": endereco_destino,
            },
            "descricao": descricao
        }

        # Adicionar informações específicas por tipo
        if tipo_transferencia == 'saldo_interno':
            response["valor"] = valor
            response["valor_wei"] = int(valor_wei)
            # Consultar saldos internos atualizados
            response["origem"]["saldo_interno_eth"] = float(w3.from_wei(
                etherFlow.functions.consultarSaldoInterno(endereco_origem).call(), 'ether'
            ))
            response["destino"]["saldo_interno_eth"] = float(w3.from_wei(
                etherFlow.functions.consultarSaldoInterno(endereco_destino).call(), 'ether'
            ))
        else:
            response["valor_eth"] = valor_eth
            response["valor_wei"] = int(valor_wei)
            # Consultar saldos ETH das wallets
            response["origem"]["saldo_wallet_eth"] = float(w3.from_wei(
                w3.eth.get_balance(endereco_origem), 'ether'
            ))
            response["destino"]["saldo_wallet_eth"] = float(w3.from_wei(
                w3.eth.get_balance(endereco_destino), 'ether'
            ))

        # Adicionar cotação se disponível
        if valor_reais:
            response["valor_reais_equivalente"] = round(valor_reais, 2)
            response["cotacao_eth_brl"] = round(eth_brl, 2)

        return jsonify(response)

    except Exception as e:
        return jsonify({"erro": f"Erro ao processar transação: {str(e)}"}), 500

# Nova rota para listar transações de um cliente
@app.route("/getTransacoesCliente", methods=["GET"])
def getTransacoesCliente():
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

"""""
tx = etherFlow.functions.setContaOng(ongWallet).build_transaction({
    "from": admWallet,
    "nonce": w3.eth.get_transaction_count(admWallet),
    "gas": 100000,
    "gasPrice": w3.eth.gas_price
})

signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
conta_ong = etherFlow.functions.contaOng().call()
print("Endereço da ONG configurado:", conta_ong)
"""""


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
        if not w3.is_address(endereco_cliente) or endereco_cliente == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Cliente não registrado com essa referência Pix"}), 400

        cliente_db = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
        if not cliente_db:
            return jsonify({"erro": "Cliente não encontrado no banco de dados"}), 400

        private_key_cliente = cliente_db.private_key

        # Conversão BRL → ETH → WEI
        cotacao = get_eth_to_brl()
        valor_eth = valor_reais / cotacao
        valor_wei = w3.to_wei(valor_eth, 'ether')

        # Criar transação de doação direta
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
        signed_tx = sign_n_send(tx, private_key_cliente)

        # Registrar no banco
        try:
            nova_transacao = Transacao(
                valor_pagamento=valor_reais,
                descricao="Doação para ONG",
                beneficiado="ONG",  # você pode opcionalmente buscar o endereço real abaixo
                hash_transacao=signed_tx["transactionHash"].hex(),
                cliente_id=cliente_db.id
            )
            db.session.add(nova_transacao)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao registrar no BD: {str(e)}")

        # Buscar endereço da ONG do contrato
        endereco_ong = etherFlow.functions.contaOng().call()

        return jsonify({
            "status": "Doação realizada com sucesso!",
            "valor_wei": int(valor_wei),
            "valor_eth": str(valor_eth),
            "valor_brl": round(valor_reais, 2),
            "cotacao": cotacao,
            "transaction_hash": signed_tx["transactionHash"].hex(),
            "gas_usado": signed_tx.get("gasUsed", "N/A"),
            "endereco_doador": endereco_cliente,
            "endereco_ong": endereco_ong
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao processar a doação: {str(e)}"}), 500

@app.route("/ethereum_brl_mensal", methods=["GET"])
def ethereum_brl_mensal():
    try:
        # Meses e valores em BRL
        meses = [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set"
        ]
        valores_brl = [
            3298.26*5.5, 2237.90*5.5, 1823.48*5.5, 1793.78*5.5,
            2529.09*5.5, 2486.46*5.5, 3696.71*5.5, 4497.18*5.5,
            4590.00*5.5
        ]

        # Criar o gráfico
        plt.figure(figsize=(9,5))
        plt.plot(meses, valores_brl, marker="o", color="blue", linewidth=2)
        plt.title("Ethereum (ETH) em BRL - Janeiro a Setembro 2025", fontsize=14)
        plt.xlabel("Mês")
        plt.ylabel("Preço (R$)")
        plt.grid(True)

        # Salvar em memória
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        plt.close()

        return Response(buffer.getvalue(), mimetype="image/png")

    except Exception as e:
        return {"error": str(e)}, 500

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