import mysql.connector

def conectar():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="root", # root
        database="sistema_blockchain_cliente"
    )
