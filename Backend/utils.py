# Funções auxiliares
from Backend.my_blockchain import w3
import requests
import qrcode
import os
from PIL import Image

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
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)
        return receipt
    except Exception as e:
        print("Erro ao aguardar confirmação da transação:", e)
        return None

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

def gerar_qrcode(link: str, nome_arquivo: str = "qrcode.png") -> str:
    """
    Gera um QR code com o link fornecido e salva em /static/qrcodes/.
    Retorna o caminho completo do arquivo.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="cyan").convert("RGB")
    caminho = os.path.join("static", "qrcodes", nome_arquivo)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    img.save(caminho)
    print(f"QR code salvo em: {caminho}")
    return caminho

def salvar_qr(img, nome_arquivo):
    pasta = os.path.join("static", "qrcodes")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome_arquivo)
    img.save(caminho)
    print(f"QR salvo em: {caminho}")
    return caminho

def qr_degrade(data):
    qr = qrcode.make(data).convert("RGBA")
    width, height = qr.size
    gradient = Image.new("RGBA", qr.size)
    for x in range(width):
        for y in range(height):
            r = int(255 * (x / width))
            b = 255 - r
            gradient.putpixel((x, y), (r, 0, b, 255))
    pixels_qr = qr.load()
    pixels_grad = gradient.load()
    for x in range(width):
        for y in range(height):
            if pixels_qr[x, y][0] > 128:
                pixels_grad[x, y] = (255, 255, 255, 0)
    caminho = salvar_qr(gradient, "registro_degrade.png")
    return caminho

def qr_padrao(data, nome_arquivo):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    caminho = salvar_qr(img, nome_arquivo)
    return caminho

def getGanacheAccount():
    global nextIndexAccount
    if nextIndexAccount >= len(w3.eth.accounts):
        raise Exception(f"Não há mais contas disponíveis no Ganache. Máximo: {len(w3.eth.accounts)}")

    # Obtenção do endereço da conta
    AccountAddress = w3.eth.accounts[nextIndexAccount]

    # Obtençao da private key da conta
    try:
        privateKeyUser = w3.geth.personal.export_account(AccountAddress, "")
    # Except caso as contas não sejam corretamente acessadas
    except:

        GanacheKey = {
            3: "0xf553d0e7ee019f9150e5873cd5dc45662a625cb6c5e9833d956ccb2a14bf53b3",
            4: "0x4c45293624bf4eeb1cd7dcada4a2897c4b558ae62d3a3a1b91d425351b2162a1",
            5: "0x98f7b85ba123c94f8c93fbdb98efca82d65937d34975a19b8e9e050ca3ce7d3c"
        }

        if nextIndexAccount not in GanacheKey:
            raise Exception(f"Chave privada não encontrada para a conta {nextIndexAccount}")

        privateKeyUser = GanacheKey[nextIndexAccount]

    thisAccount = nextIndexAccount
    nextIndexAccount += 1

    print(f"📝 Atribuindo conta {thisAccount} do Ganache: {AccountAddress}")

    return AccountAddress, privateKeyUser

"""
if __name__ == "__main__":
    url = "https://cryp2real.flutterflow.app/register"
    print(f"Rodando no diretório: {os.getcwd()}")
    qr_degrade(url)
"""