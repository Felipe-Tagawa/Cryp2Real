from configBD import db_config
from mysql.connector import Error as MySQLError
from web3 import Web3
from typing import Optional, Dict, List
import hashlib
import datetime


class ClienteDAO:

    def __init__(self):
        self.w3 = Web3()

    def criar_cliente(self, nome: str, email: str, referencia_pix: str, senha: str, carteira_endereco: str) -> Optional[
        int]:
        """
        Cria um novo cliente no banco de dados

        Args:
            nome: Nome completo do cliente
            email: Email do cliente
            referencia_pix: Referência PIX única
            senha: Senha do cliente (será hashada)
            carteira_endereco: Endereço da carteira Ethereum

        Returns:
            ID do cliente criado ou None em caso de erro
        """
        try:
            # Hash da senha
            senha_hash = hashlib.sha256(senha.encode()).hexdigest()

            with db_config.get_cursor() as cursor:
                query = """
                INSERT INTO clientes 
                (nome, email, referencia_pix, senha_hash, carteira_endereco, saldo_wei, saldo_ether, saldo_reais)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """

                values = (
                    nome,
                    email,
                    referencia_pix,
                    senha_hash,
                    carteira_endereco,
                    0,  # saldo_wei inicial
                    0.0,  # saldo_ether inicial
                    0.0  # saldo_reais inicial
                )

                cursor.execute(query, values)
                return cursor.lastrowid

        except MySQLError as e:
            print(f"Erro ao criar cliente: {e}")
            return None

    def buscar_cliente_por_email(self, email: str) -> Optional[Dict]:
        """
        Busca um cliente pelo email

        Args:
            email: Email do cliente

        Returns:
            Dicionário com dados do cliente ou None se não encontrado
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                SELECT id, nome, email, referencia_pix, carteira_endereco, 
                       saldo_wei, saldo_ether, saldo_reais, registrado, 
                       data_criacao, data_atualizacao, ativo
                FROM clientes 
                WHERE email = %s AND ativo = TRUE
                """

                cursor.execute(query, (email,))
                return cursor.fetchone()

        except MySQLError as e:
            print(f"Erro ao buscar cliente por email: {e}")
            return None

    def buscar_cliente_por_carteira(self, carteira_endereco: str) -> Optional[Dict]:
        """
        Busca um cliente pelo endereço da carteira

        Args:
            carteira_endereco: Endereço da carteira Ethereum

        Returns:
            Dicionário com dados do cliente ou None se não encontrado
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                SELECT id, nome, email, referencia_pix, carteira_endereco, 
                       saldo_wei, saldo_ether, saldo_reais, registrado, 
                       data_criacao, data_atualizacao, ativo
                FROM clientes 
                WHERE carteira_endereco = %s AND ativo = TRUE
                """

                cursor.execute(query, (carteira_endereco,))
                return cursor.fetchone()

        except MySQLError as e:
            print(f"Erro ao buscar cliente por carteira: {e}")
            return None

    def buscar_cliente_por_pix(self, referencia_pix: str) -> Optional[Dict]:
        """
        Busca um cliente pela referência PIX

        Args:
            referencia_pix: Referência PIX do cliente

        Returns:
            Dicionário com dados do cliente ou None se não encontrado
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                SELECT id, nome, email, referencia_pix, carteira_endereco, 
                       saldo_wei, saldo_ether, saldo_reais, registrado, 
                       data_criacao, data_atualizacao, ativo
                FROM clientes 
                WHERE referencia_pix = %s AND ativo = TRUE
                """

                cursor.execute(query, (referencia_pix,))
                return cursor.fetchone()

        except MySQLError as e:
            print(f"Erro ao buscar cliente por PIX: {e}")
            return None

    def atualizar_saldo(self, cliente_id: int, saldo_wei: int, saldo_ether: float, saldo_reais: float) -> bool:
        """
        Atualiza o saldo de um cliente

        Args:
            cliente_id: ID do cliente
            saldo_wei: Novo saldo em WEI
            saldo_ether: Novo saldo em ETH
            saldo_reais: Novo saldo em BRL

        Returns:
            True se atualização foi bem-sucedida, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                UPDATE clientes 
                SET saldo_wei = %s, saldo_ether = %s, saldo_reais = %s
                WHERE id = %s
                """

                cursor.execute(query, (saldo_wei, saldo_ether, saldo_reais, cliente_id))
                return cursor.rowcount > 0

        except MySQLError as e:
            print(f"Erro ao atualizar saldo: {e}")
            return False

    def incrementar_saldo(self, cliente_id: int, valor_wei: int, valor_ether: float, valor_reais: float) -> bool:
        """
        Incrementa o saldo de um cliente

        Args:
            cliente_id: ID do cliente
            valor_wei: Valor a ser adicionado em WEI
            valor_ether: Valor a ser adicionado em ETH
            valor_reais: Valor a ser adicionado em BRL

        Returns:
            True se incremento foi bem-sucedido, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                UPDATE clientes 
                SET saldo_wei = saldo_wei + %s, 
                    saldo_ether = saldo_ether + %s, 
                    saldo_reais = saldo_reais + %s
                WHERE id = %s
                """

                cursor.execute(query, (valor_wei, valor_ether, valor_reais, cliente_id))
                return cursor.rowcount > 0

        except MySQLError as e:
            print(f"Erro ao incrementar saldo: {e}")
            return False

    def decrementar_saldo(self, cliente_id: int, valor_wei: int, valor_ether: float, valor_reais: float) -> bool:
        """
        Decrementa o saldo de um cliente

        Args:
            cliente_id: ID do cliente
            valor_wei: Valor a ser subtraído em WEI
            valor_ether: Valor a ser subtraído em ETH
            valor_reais: Valor a ser subtraído em BRL

        Returns:
            True se decremento foi bem-sucedido, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                UPDATE clientes 
                SET saldo_wei = saldo_wei - %s, 
                    saldo_ether = saldo_ether - %s, 
                    saldo_reais = saldo_reais - %s
                WHERE id = %s AND saldo_wei >= %s
                """

                cursor.execute(query, (valor_wei, valor_ether, valor_reais, cliente_id, valor_wei))
                return cursor.rowcount > 0

        except MySQLError as e:
            print(f"Erro ao decrementar saldo: {e}")
            return False

    def verificar_saldo_suficiente(self, cliente_id: int, valor_wei: int) -> bool:
        """
        Verifica se o cliente tem saldo suficiente para uma transação

        Args:
            cliente_id: ID do cliente
            valor_wei: Valor a ser verificado em WEI

        Returns:
            True se tem saldo suficiente, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = "SELECT saldo_wei FROM clientes WHERE id = %s"
                cursor.execute(query, (cliente_id,))

                resultado = cursor.fetchone()
                if resultado:
                    return int(resultado['saldo_wei']) >= valor_wei
                return False

        except MySQLError as e:
            print(f"Erro ao verificar saldo: {e}")
            return False

    def listar_clientes(self, ativo: bool = True, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Lista clientes com paginação

        Args:
            ativo: Se deve listar apenas clientes ativos
            limit: Limite de registros por página
            offset: Deslocamento para paginação

        Returns:
            Lista de dicionários com dados dos clientes
        """
        try:
            with db_config.get_cursor() as cursor:
                query = """
                SELECT id, nome, email, referencia_pix, carteira_endereco, 
                       saldo_wei, saldo_ether, saldo_reais, registrado, 
                       data_criacao, data_atualizacao, ativo
                FROM clientes 
                WHERE ativo = %s
                ORDER BY data_criacao DESC
                LIMIT %s OFFSET %s
                """

                cursor.execute(query, (ativo, limit, offset))
                return cursor.fetchall()

        except MySQLError as e:
            print(f"Erro ao listar clientes: {e}")
            return []

    def desativar_cliente(self, cliente_id: int) -> bool:
        """
        Desativa um cliente (soft delete)

        Args:
            cliente_id: ID do cliente

        Returns:
            True se desativação foi bem-sucedida, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = "UPDATE clientes SET ativo = FALSE WHERE id = %s"
                cursor.execute(query, (cliente_id,))
                return cursor.rowcount > 0

        except MySQLError as e:
            print(f"Erro ao desativar cliente: {e}")
            return False

    def verificar_email_existe(self, email: str) -> bool:
        """
        Verifica se um email já está em uso

        Args:
            email: Email a ser verificado

        Returns:
            True se email já existe, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = "SELECT COUNT(*) as count FROM clientes WHERE email = %s"
                cursor.execute(query, (email,))

                resultado = cursor.fetchone()
                return resultado['count'] > 0

        except MySQLError as e:
            print(f"Erro ao verificar email: {e}")
            return False

    def verificar_pix_existe(self, referencia_pix: str) -> bool:
        """
        Verifica se uma referência PIX já está em uso

        Args:
            referencia_pix: Referência PIX a ser verificada

        Returns:
            True se PIX já existe, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = "SELECT COUNT(*) as count FROM clientes WHERE referencia_pix = %s"
                cursor.execute(query, (referencia_pix,))

                resultado = cursor.fetchone()
                return resultado['count'] > 0

        except MySQLError as e:
            print(f"Erro ao verificar PIX: {e}")
            return False

    def verificar_carteira_existe(self, carteira_endereco: str) -> bool:
        """
        Verifica se um endereço de carteira já está em uso

        Args:
            carteira_endereco: Endereço da carteira a ser verificado

        Returns:
            True se carteira já existe, False caso contrário
        """
        try:
            with db_config.get_cursor() as cursor:
                query = "SELECT COUNT(*) as count FROM clientes WHERE carteira_endereco = %s"
                cursor.execute(query, (carteira_endereco,))

                resultado = cursor.fetchone()
                return resultado['count'] > 0

        except MySQLError as e:
            print(f"Erro ao verificar carteira: {e}")
            return False