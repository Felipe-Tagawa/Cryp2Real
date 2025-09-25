import hashlib
import io
import os
import secrets
import traceback
from datetime import datetime, timezone

from dotenv import load_dotenv

from flask import Flask, jsonify, request, session, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from matplotlib import pyplot as plt
from sqlalchemy import text

from Backend.my_blockchain import w3, etherFlow, sistema_cliente, PRIVATE_KEY, admWallet, ongWallet
from Backend.utils import sign_n_send, get_eth_to_brl, getGanacheAccount, calcular_projecao, gerar_qr_comprovante

load_dotenv()

db = SQLAlchemy()


class Config:
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI',
                                                 "mysql+pymysql://root:nLLldXjrPdDgYwBpubKiqMhKgEqFdMXE@switchyard.proxy.rlwy.net:39347/sistema_blockchain_cliente")
        print("🚀 Conectando ao banco de produção (Railway)")
    else:
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
    saldo_ether = db.Column(db.Float, default=0.0)
    saldo_reais = db.Column(db.Float, default=0.0)
    carteira = db.Column(db.String(42), nullable=False)
    private_key = db.Column(db.Text, nullable=False)

    # Relacionamento com transações
    transacoes = db.relationship('Transacao', backref='cliente', lazy=True)


class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor_pagamento = db.Column(db.Double, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    beneficiado = db.Column(db.String(100), nullable=False)
    data_transacao = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    hash_transacao = db.Column(db.String(66), nullable=False)
    tipo_transacao = db.Column(db.String(100), nullable=False)

    # Chave estrangeira para o cliente
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)

    def __repr__(self):
        return f'<Transacao {self.id}: R${self.valor_pagamento} para {self.beneficiado}>'


api_cache = {}
api_locks = {}
CACHE_DURATION = 2  # segundos

@app.route('/')
def run():
    try:
        return 'API funcionando com sucesso!'
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Falha ao carregar API", "detalhes": str(e)}), 500

@app.route("/test-db")
def test_db():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "Conexão com banco OK!"
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro na conexão com o banco", "detalhes": str(e)}), 500

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
        traceback.print_exc()
        return jsonify({"erro": "Erro ao conectar com Ganache", "detalhes": str(e)}), 500


@app.route("/registrarCliente", methods=["POST"])
def registro_cliente():
    """
    Registra um novo cliente no sistema (blockchain + banco de dados).

    Args:
        Nenhum argumento direto. Recebe JSON no body com:
            nome (str): Nome do cliente (mínimo 2 caracteres).
            referenciaPix (str): Chave PIX única do cliente.
            email (str): Email do cliente (único).
            senha (str): Senha em texto plano (mínimo 6 caracteres).

    Returns:
        flask.Response: JSON com dados do cliente registrado ou erro.
            200: Registro bem-sucedido.
            400: Erro de validação ou duplicidade.
            500: Erro interno ao salvar no blockchain ou banco de dados.
    """
    try:
        data = request.get_json()
        nome = data.get("nome", "").strip()
        referenciaPix = data.get("referenciaPix", "").strip()
        email = data.get("email", "").strip()
        senha = data.get("senha", "").strip()

        senhaHash = hashlib.sha256(senha.encode('utf-8')).hexdigest()

        # Validações
        if not nome or len(nome) < 2:
            return jsonify({"erro": "Nome deve ter pelo menos 2 caracteres"}), 400
        if not referenciaPix:
            return jsonify({"erro": "Referência PIX não pode estar vazia"}), 400
        if not email:
            return jsonify({"erro": "Email é obrigatório"}), 400
        if not senha or len(senha) < 6:
            return jsonify({"erro": "Senha deve ter pelo menos 6 caracteres"}), 400

        # Verificar se já existe no blockchain
        try:
            endereco_existente = sistema_cliente.functions.getEnderecoPorPix(referenciaPix).call()
            if endereco_existente != "0x0000000000000000000000000000000000000000":
                return jsonify({"erro": f"Referência PIX '{referenciaPix}' já está cadastrada no blockchain!"}), 400
        except Exception as e:
            print(f"Erro ao verificar PIX no blockchain: {e}")

        # Verificar se já existe no banco
        existing_client = Cliente.query.filter_by(referenciaPix=referenciaPix).first()
        if existing_client:
            return jsonify({"erro": f"Referência PIX '{referenciaPix}' já está cadastrada no banco!"}), 400

        existing_email = Cliente.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({"erro": f"Email '{email}' já está cadastrado!"}), 400

        # Obter conta do Ganache
        userAddress, privateKeyUser = getGanacheAccount()

        # Construir transação com gas otimizado
        try:
            transaction = sistema_cliente.functions.registrarCliente(
                nome, referenciaPix, email, senha
            ).build_transaction({
                "from": userAddress,
                "nonce": w3.eth.get_transaction_count(userAddress),
                "gasPrice": w3.eth.gas_price,
                "gas": 800000,  # Gas aumentado para registro
                "chainId": w3.eth.chain_id,
            })
        except ValueError as e:
            if "revert" in str(e).lower():
                return jsonify({"erro": "Dados inválidos para registro no blockchain"}), 400
            else:
                return jsonify({"erro": f"Erro ao construir transação: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"erro": f"Erro inesperado: {str(e)}"}), 500

        # Enviar transação
        try:
            receipt = sign_n_send(transaction, privateKeyUser)
        except ValueError as e:
            return jsonify({"erro": f"Transação rejeitada: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"erro": f"Erro ao enviar transação: {str(e)}"}), 500

        # Salvar no banco
        try:
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
                "saldo_inicial_eth": float(w3.from_wei(w3.eth.get_balance(userAddress), 'ether')),
                "tx_registro": receipt["transactionHash"].hex(),
                "referenciaPix": referenciaPix,
                "nome": nome,
                "email": email
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar no banco: {str(e)}")
            return jsonify({"erro": f"Usuário criado na blockchain mas erro ao salvar no banco: {str(e)}"}), 500

    except Exception as e:
        db.session.rollback()
        print("❌ Erro em /registrarCliente:", str(e))
        traceback.print_exc()
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500



@app.route("/cliente_registrado", methods=["GET"])
def cliente_registrado():
    """
    Verifica se um cliente está registrado com sucesso no sistema (DEBUG).

    Args:
        Nenhum argumento direto. Recebe JSON no body com:
            endereco (str): Endereço da conta do cliente em questão.
    Returns:
        flask.Response: JSON com endereço e boolean de registrado ou erro.
            200: Usuário registrado.
            400: Erro de validação de endereço.
            500: Erro interno ao verificar o registro do usuário.
    """
    try:
        endereco = request.args.get("endereco")
        if not endereco:
            return jsonify({"erro": "Parâmetro 'endereco' obrigatório"}), 400

        endereco = w3.to_checksum_address(endereco)
        registrado = sistema_cliente.functions.ClienteRegistrado(endereco).call()
        return jsonify({
            "endereco": endereco,
            "registrado": registrado
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao verificar registro: {str(e)}"}), 500



@app.route("/mostraInfoCliente", methods=["GET"])
def mostraInfoCliente():
    """
        Retorna informações detalhadas de um cliente a partir da referência Pix.

        Args:
            referenciaPix (str): Passado via query string (?referenciaPix=...).
                Identificador Pix único do cliente.

        Returns:
            flask.Response: JSON contendo:
                - nome (str): Nome do cliente.
                - email (str): Email do cliente.
                - referenciaPix (str): Referência Pix.
                - carteira (str): Endereço Ethereum.
                - registrado (bool): Status de registro.
                - saldo_eth (float): Saldo da carteira em ETH.
            Erros:
                400: Parâmetro ausente.
                404: Cliente não encontrado.
                500: Erro interno.
        """
    try:
        referencia_pix = request.args.get("referenciaPix")

        if not referencia_pix:
            return jsonify({"erro": "Parâmetro 'referenciaPix' é obrigatório!"}), 400

        # Buscar o endereço associado à referência Pix
        endereco = sistema_cliente.functions.getEnderecoPorPix(referencia_pix).call()

        if not w3.is_address(endereco) or endereco == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Nenhum cliente encontrado para essa referenciaPix"}), 404

        endereco = w3.to_checksum_address(endereco)

        # Chama o contrato para pegar as informações
        dados = sistema_cliente.functions.mostraInfoCliente(referencia_pix).call()
        carteiraContrato, nome, saldo_eth_wei, registrado, referenciaPix, email = dados

        return jsonify({
            "nome": nome,
            "email": email,
            "referenciaPix": referenciaPix,
            "carteira": carteiraContrato,
            "registrado": registrado,
            "saldo_eth": float(w3.from_wei(saldo_eth_wei, 'ether'))
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao buscar informações do cliente: {str(e)}"}), 500

@app.route("/getName", methods=["GET"])
def getName():
    """
        Retorna o nome de um cliente pelo Pix.

        Args:
            referenciaPix (str): Passado via query string.
                Identificador Pix do cliente.

        Returns:
            flask.Response: JSON contendo:
                - status (str): "sucesso".
                - cliente_id (int): ID no banco de dados.
                - referenciaPix (str): Referência Pix.
                - nome (str): Nome do cliente (contrato > banco).
            Erros:
                400: Parâmetro ausente.
                404: Cliente não encontrado.
                500: Erro interno.
        """

    try:
        referencia_pix = request.args.get("referenciaPix")
        if not referencia_pix:
            return jsonify({"erro": "referenciaPix obrigatória na query string"}), 400

        try:
            cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if not cliente:
                return jsonify({"erro": "Cliente não encontrado"}), 404

            try:
                endereco = sistema_cliente.functions.getEnderecoPorPix(referencia_pix).call()
                if endereco != "0x0000000000000000000000000000000000000000":
                    nome_contrato = sistema_cliente.functions.getNomeCliente(endereco).call()
                else:
                    nome_contrato = None
            except Exception as e:
                nome_contrato = None
                print(f"Erro ao buscar nome no contrato: {e}")

            return jsonify({
                "status": "sucesso",
                "cliente_id": cliente.id,
                "referenciaPix": cliente.referenciaPix,
                "nome": nome_contrato if nome_contrato else cliente.nome
            }), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({"erro": f"Erro interno ao buscar cliente: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /getName", "detalhes": str(e)}), 500


@app.route("/getBalance", methods=["GET"])
def getBalance():
    """
        Retorna o saldo de um cliente em ETH e BRL.

        Args:
            referenciaPix (str, opcional): Passado via query string.
                Se ausente, usa o cliente da sessão.

        Returns:
            flask.Response: JSON contendo:
                - status (str): "sucesso".
                - cliente_id (int), nome (str), email (str).
                - referenciaPix (str).
                - carteira (str): Endereço Ethereum.
                - balance_eth (float): Saldo em ETH.
                - balance_brl (float): Saldo convertido em BRL.
                - cotacao_eth_brl (float): Cotação usada.
                - fonte_dados (str).
                - timestamp (str, ISO8601).
            Erros:
                400: Parâmetro ou sessão inválida.
                404: Cliente não encontrado.
                500: Erro interno.
        """

    try:
        referencia_pix = request.args.get('referenciaPix')
        print(f" referencia_pix: {referencia_pix}")

        if referencia_pix:
            cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if not cliente:
                return jsonify({"erro": "Cliente não encontrado"}), 404
        else:
            cliente_id = session.get("cliente_id")
            print(f"🔍 DEBUG - session cliente_id: {cliente_id}")
            if not cliente_id:
                return jsonify({"erro": "referenciaPix obrigatória na query string ou sessão válida"}), 400
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return jsonify({"erro": "Cliente da sessão não encontrado"}), 404

        try:
            address = w3.to_checksum_address(cliente.carteira)
            saldo_wei = w3.eth.get_balance(address)
            saldo_eth = w3.from_wei(saldo_wei, "ether")
            cotacao_eth_brl = get_eth_to_brl()
            print(f"🔍 Cotação obtida: R$ {cotacao_eth_brl:,.2f}")
            saldo_brl = float(saldo_eth) * cotacao_eth_brl

            return jsonify({
                "status": "sucesso",
                "cliente_id": cliente.id,
                "nome": cliente.nome,
                "email": cliente.email,
                "referenciaPix": cliente.referenciaPix,
                "carteira": address,
                "balance_eth": float(saldo_eth),
                "balance_brl": round(saldo_brl, 2),
                "cotacao_eth_brl": cotacao_eth_brl,
                "fonte_dados": "ganache_blockchain_eth_real",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({"erro": f"Erro ao obter saldo do blockchain: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /getBalance", "detalhes": str(e)}), 500

@app.route("/transferirEntreUsers", methods=["POST"])
def transferirEntreUsers():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados JSON não fornecidos"}), 400

        required_fields = ['referencia_origem', 'referencia_destino', 'tipo_transferencia', 'valor_eth']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"erro": f"Campo '{field}' é obrigatório"}), 400

        referencia_origem = data['referencia_origem']
        referencia_destino = data['referencia_destino']
        tipo_transferencia = data['tipo_transferencia']

        try:
            valor_eth = float(data['valor_eth'])
            if valor_eth <= 0:
                return jsonify({"erro": "Valor deve ser maior que zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "valor_eth deve ser um número válido"}), 400

        valor_wei = w3.to_wei(valor_eth, 'ether')
        descricao = data.get('descricao', '')

        if referencia_origem == referencia_destino:
            return jsonify({"erro": "Não é possível transferir para si mesmo"}), 400

        try:
            endereco_origem = sistema_cliente.functions.getEnderecoPorPix(referencia_origem).call()
            endereco_destino = sistema_cliente.functions.getEnderecoPorPix(referencia_destino).call()
        except Exception as e:
            return jsonify({"erro": f"Erro ao buscar endereços: {str(e)}"}), 500

        if not w3.is_address(endereco_origem) or endereco_origem == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Usuário de origem não registrado"}), 400
        if not w3.is_address(endereco_destino) or endereco_destino == "0x0000000000000000000000000000000000000000":
            return jsonify({"erro": "Usuário de destino não registrado"}), 400

        cliente_origem = Cliente.query.filter_by(referenciaPix=referencia_origem).first()
        if not cliente_origem:
            return jsonify({"erro": "Cliente origem não encontrado no banco de dados"}), 400

        try:
            saldo_origem = w3.eth.get_balance(endereco_origem)
            gas_estimate = 300000
            gas_cost = gas_estimate * w3.eth.gas_price
            total_necessario = valor_wei + gas_cost

            if saldo_origem < total_necessario:
                return jsonify({
                    "erro": "Saldo ETH insuficiente",
                    "saldo_atual_eth": float(w3.from_wei(saldo_origem, 'ether')),
                    "valor_transferencia": valor_eth,
                    "gas_estimado_eth": float(w3.from_wei(gas_cost, 'ether')),
                    "total_necessario_eth": float(w3.from_wei(total_necessario, 'ether'))
                }), 400
        except Exception as e:
            return jsonify({"erro": f"Erro ao verificar saldo: {str(e)}"}), 500

        try:
            nonce = w3.eth.get_transaction_count(endereco_origem)
            if tipo_transferencia == 'eth_direto':
                transaction = etherFlow.functions.transferirETHDireto(
                    referencia_origem,
                    w3.to_checksum_address(endereco_destino)
                ).build_transaction({
                    "from": endereco_origem,
                    "nonce": nonce,
                    "gasPrice": w3.eth.gas_price,
                    "value": valor_wei,
                    "gas": 400000
                })
            elif tipo_transferencia == 'sem_taxas':
                transaction = etherFlow.functions.transferenciaSemTaxas(
                    referencia_origem,
                    w3.to_checksum_address(endereco_destino)
                ).build_transaction({
                    "from": endereco_origem,
                    "nonce": nonce,
                    "gasPrice": w3.eth.gas_price,
                    "value": valor_wei,
                    "gas": 300000
                })
            else:
                return jsonify({"erro": "Tipo de transferência inválido. Use: 'eth_direto' ou 'sem_taxas'"}), 400
        except ValueError as e:
            if "revert" in str(e).lower():
                return jsonify({
                    "erro": "Transação rejeitada pelo contrato",
                    "detalhes": "Verifique se os usuários estão registrados e os dados estão corretos",
                    "erro_tecnico": str(e)
                }), 400
            else:
                return jsonify({"erro": f"Erro ao construir transação: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"erro": f"Erro inesperado: {str(e)}"}), 500

        try:
            receipt = sign_n_send(transaction, cliente_origem.private_key)
        except ValueError as e:
            return jsonify({"erro": f"Transação rejeitada pela blockchain: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"erro": f"Erro ao enviar transação: {str(e)}"}), 500

        try:
            eth_brl = get_eth_to_brl() if 'get_eth_to_brl' in globals() else 1.0
            valor_reais = valor_eth * eth_brl

            transacao_saida = Transacao(
                valor_pagamento=valor_reais,
                descricao=f"Transferência {tipo_transferencia} para {referencia_destino}: {descricao}",
                beneficiado=f"Usuário {referencia_destino}",
                hash_transacao=receipt["transactionHash"].hex(),
                cliente_id=cliente_origem.id,
                tipo_transacao="SAIDA"
            )
            db.session.add(transacao_saida)

            cliente_destino = Cliente.query.filter_by(referenciaPix=referencia_destino).first()
            if cliente_destino:
                transacao_entrada = Transacao(
                    valor_pagamento=valor_reais,
                    descricao=f"Recebido {tipo_transferencia} de {referencia_origem}: {descricao}",
                    beneficiado=f"Usuário {referencia_origem}",
                    hash_transacao=receipt["transactionHash"].hex(),
                    cliente_id=cliente_destino.id,
                    tipo_transacao="ENTRADA"
                )
                db.session.add(transacao_entrada)

            db.session.commit()
            print("✅ Transações registradas no BD com sucesso")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao registrar no BD: {str(e)}")

        receipt_data = {
            "hash_transacao": receipt["transactionHash"].hex(),
            "valor_eth": valor_eth,
            "valor_reais": round(valor_reais, 2),
            "de": referencia_origem,
            "para": referencia_destino,
            "tipo_transferencia": tipo_transferencia,
            "descricao": descricao
        }
        qr_base64, qr_path = gerar_qr_comprovante(receipt_data, receipt["transactionHash"].hex())

        return jsonify({
            "status": "sucesso",
            "tipo_transferencia": tipo_transferencia,
            "valor_reais": round(valor_reais, 2),
            "valor_eth": valor_eth,
            "valor_wei": int(valor_wei),
            "transaction_hash": receipt["transactionHash"].hex(),
            "gas_usado": receipt.get("gasUsed", 0),
            "descricao": descricao,
            "beneficiado": f"Usuário {referencia_destino}",
            "origem": {
                "referencia": referencia_origem,
                "endereco": endereco_origem
            },
            "destino": {
                "referencia": referencia_destino,
                "endereco": endereco_destino
            },
            "qr_comprovante": qr_base64,
            "qr_path": qr_path
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /transferirEntreUsers", "detalhes": str(e)}), 500


@app.route("/getTransacoesCliente", methods=["GET"])
def getTransacoesCliente():
    """
        Retorna todas as transações de um cliente.

        Args:
            referenciaPix (str): Passado via query string.

        Returns:
            flask.Response: JSON contendo:
                - cliente (str).
                - referencia_pix (str).
                - total_transacoes (int).
                - transacoes (list[dict]): Detalhes de cada transação.
            Erros:
                400: Parâmetro ausente.
                404: Cliente não encontrado.
                500: Erro interno.
        """

    try:
        referencia_pix = request.args.get("referenciaPix")
        if not referencia_pix:
            return jsonify({"erro": "Parâmetro 'referenciaPix' é obrigatório!"}), 400

        try:
            cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if not cliente:
                return jsonify({"erro": "Cliente não encontrado"}), 404

            transacoes = Transacao.query.filter_by(cliente_id=cliente.id).order_by(
                Transacao.data_transacao.desc()).all()

            transacoes_list = []
            for transacao in transacoes:
                transacoes_list.append({
                    "id": transacao.id,
                    "valor_pagamento": float(transacao.valor_pagamento),
                    "descricao": transacao.descricao,
                    "beneficiado": transacao.beneficiado,
                    "data_transacao": transacao.data_transacao.isoformat(),
                    "hash_transacao": transacao.hash_transacao,
                    "tipo_transacao": transacao.tipo_transacao
                })

            return jsonify({
                "cliente": cliente.nome,
                "referencia_pix": cliente.referenciaPix,
                "total_transacoes": len(transacoes_list),
                "transacoes": transacoes_list
            })
        except Exception as e:
            traceback.print_exc()
            return jsonify({"erro": f"Erro ao buscar transações: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /getTransacoesCliente", "detalhes": str(e)}), 500

# === Bloco de configuração inicial do contrato (doação / conta ONG) com proteção ===
try:
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
except Exception as e:
    print("⚠️ Falha ao configurar conta ONG (ignorado):", str(e))
    traceback.print_exc()


@app.route("/donate", methods=["POST"])
def donate():
    """
        Realiza uma doação de um cliente para a ONG configurada.

        Args:
            JSON (dict): Body da requisição contendo:
                - valorReais (float): Valor em BRL.
                - referenciaPix (str): Chave Pix do cliente.

        Returns:
            flask.Response: JSON contendo:
                - status (str).
                - valor_wei (int), valor_eth (str), valor_brl (float).
                - cotacao (str).
                - transaction_hash (str).
                - gas_usado (int ou "N/A").
                - endereco_doador (str).
                - endereco_ong (str).
            Erros:
                400: Dados inválidos.
                500: Erro interno.
        """

    try:
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
            endereco_cliente = sistema_cliente.functions.getEnderecoPorPix(referencia_pix).call()
            if not w3.is_address(endereco_cliente) or endereco_cliente == "0x0000000000000000000000000000000000000000":
                return jsonify({"erro": "Cliente não registrado com essa referência Pix"}), 400

            cliente_db = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if not cliente_db:
                return jsonify({"erro": "Cliente não encontrado no banco de dados"}), 400

            private_key_cliente = cliente_db.private_key

            valor_eth = valor_reais
            valor_wei = w3.to_wei(valor_eth, 'ether')

            nonce = w3.eth.get_transaction_count(endereco_cliente)
            tx = etherFlow.functions.doacaoDireta().build_transaction({
                "from": endereco_cliente,
                "value": int(valor_wei),
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": w3.eth.gas_price,
                "chainId": w3.eth.chain_id
            })

            signed_tx = sign_n_send(tx, private_key_cliente)

            try:
                nova_transacao = Transacao(
                    valor_pagamento=valor_reais,
                    descricao="Doação para ONG",
                    beneficiado="ONG",
                    hash_transacao=signed_tx["transactionHash"].hex(),
                    cliente_id=cliente_db.id
                )
                db.session.add(nova_transacao)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao registrar no BD: {str(e)}")

            endereco_ong = etherFlow.functions.contaOng().call()

            return jsonify({
                "status": "Doação realizada com sucesso!",
                "valor_wei": int(valor_wei),
                "valor_eth": str(valor_eth),
                "valor_brl": round(valor_reais, 2),
                "cotacao": "1 ETH = 1 BRL (fixo)",
                "transaction_hash": signed_tx["transactionHash"].hex(),
                "gas_usado": signed_tx.get("gasUsed", "N/A"),
                "endereco_doador": endereco_cliente,
                "endereco_ong": endereco_ong
            })

        except Exception as e:
            traceback.print_exc()
            return jsonify({"erro": f"Erro ao processar a doação: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /donate", "detalhes": str(e)}), 500



@app.route("/ethereum_brl_mensal", methods=["GET"])
def ethereum_brl_mensal():
    """
        Retorna um gráfico da cotação ETH em BRL de Janeiro a Setembro de 2025.

        Args:
            Nenhum.

        Returns:
            flask.Response: Imagem PNG do gráfico.
            Erros:
                500: Erro interno ao gerar gráfico.
        """

    try:
        meses = [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set"
        ]
        valores_brl = [
            3298.26 * 5.5, 2237.90 * 5.5, 1823.48 * 5.5, 1793.78 * 5.5,
            2529.09 * 5.5, 2486.46 * 5.5, 3696.71 * 5.5, 4497.18 * 5.5,
            4590.00 * 5.5
        ]

        try:
            plt.figure(figsize=(9, 5))
            plt.plot(meses, valores_brl, marker="o", color="blue", linewidth=2)
            plt.title("Ethereum (ETH) em BRL - Janeiro a Setembro 2025", fontsize=14)
            plt.xlabel("Mês")
            plt.ylabel("Preço (R$)")
            plt.grid(True)

            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", bbox_inches="tight")
            buffer.seek(0)
            plt.close()

            return Response(buffer.getvalue(), mimetype="image/png")
        except Exception as e:
            traceback.print_exc()
            return jsonify({"erro": f"Erro ao gerar gráfico: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /ethereum_brl_mensal", "detalhes": str(e)}), 500

@app.route("/currentETH", methods=["GET"])
def getCurrentETH():
    """
    Retorna a cotação atual do Ethereum em BRL.
    Returns:
        flask.Response: JSON com:
            - ethereum_brl (float): Cotação atual
            - fonte (str): Fonte dos dados
            - timestamp (str): Timestamp da consulta
        Erros:
            Nunca retorna erro - sempre retorna um valor válido
    """
    try:
        try:
            price = get_eth_to_brl()
            return jsonify({
                "ethereum_brl": price,
                "fonte": "coingecko_api" if price > 1000 else "fallback_value",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "sucesso"
            }), 200
        except Exception as e:
            print(f"❌ Erro crítico em getCurrentETH: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "ethereum_brl": 23500.0,
                "fonte": "emergency_fallback",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "fallback",
                "erro": str(e)
            }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /currentETH", "detalhes": str(e)}), 500


@app.route('/calcular_projecao', methods=['POST'])
def projectionCalculate():
    """
        Calcula projeções financeiras com base em um investimento inicial em ETH.

        Args:
            JSON (dict): Body da requisição contendo:
                - investimento_inicial_eth (float): Valor inicial em ETH.

        Returns:
            flask.Response: JSON com resultados da projeção.
            Erros:
                400: Parâmetro inválido.
                500: Erro interno.
        """

    try:
        dados = request.get_json()
        investimento_inicial = dados.get('investimento_inicial_eth')

        if investimento_inicial is None or not isinstance(investimento_inicial, (int, float)):
            return jsonify({"erro": "Parâmetro 'investimento_inicial_eth' inválido"}), 400

        resultados = calcular_projecao(investimento_inicial)
        return jsonify(resultados), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /calcular_projecao", "detalhes": str(e)}), 500

@app.route("/getUserData", methods=["GET"])
def getUserData():
    """
    Endpoint combinado que retorna nome, saldo e dados do usuário em uma única chamada
    Evita race conditions e multiple requests
    """
    try:
        referencia_pix = request.args.get('referenciaPix')

        if referencia_pix:
            cliente = Cliente.query.filter_by(referenciaPix=referencia_pix).first()
            if not cliente:
                return jsonify({"erro": "Cliente não encontrado"}), 404
        else:
            cliente_id = session.get("cliente_id")
            if not cliente_id:
                return jsonify({"erro": "Sessão inválida"}), 400
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return jsonify({"erro": "Cliente da sessão não encontrado"}), 404

        try:
            address = w3.to_checksum_address(cliente.carteira)
            saldo_wei = w3.eth.get_balance(address)
            saldo_eth = w3.from_wei(saldo_wei, "ether")
            cotacao_eth_brl = get_eth_to_brl()
            saldo_brl = float(saldo_eth) * cotacao_eth_brl

            return jsonify({
                "status": "sucesso",
                "cliente": {
                    "id": cliente.id,
                    "nome": cliente.nome,
                    "email": cliente.email,
                    "referenciaPix": cliente.referenciaPix,
                    "carteira": address
                },
                "saldo": {
                    "balance_eth": float(saldo_eth),
                    "balance_brl": round(saldo_brl, 2),
                    "cotacao_eth_brl": cotacao_eth_brl
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        except Exception as e:
            traceback.print_exc()
            return jsonify({"erro": f"Erro ao consultar blockchain/cotação: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno em /getUserData", "detalhes": str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)