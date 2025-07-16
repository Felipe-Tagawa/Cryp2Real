import mysql.connector
from mysql.connector import Error as MySQLError
import os
from contextlib import contextmanager


class DatabaseConfig:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.database = os.getenv('DB_NAME', 'sistema_blockchain_cliente')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.port = int(os.getenv('DB_PORT', '3306'))

    def get_connection(self):
        """Retorna uma conexão com o banco de dados"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            return connection
        except MySQLError as e:
            print(f"Erro ao conectar com MySQL: {e}")
            return None

    @contextmanager
    def get_cursor(self):
        """Context manager para conexão e cursor"""
        connection = self.get_connection()
        if connection is None:
            raise Exception("Não foi possível conectar ao banco de dados")

        try:
            cursor = connection.cursor(dictionary=True)
            yield cursor
            connection.commit()
        except MySQLError as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()


# Instância global da configuração
db_config = DatabaseConfig()