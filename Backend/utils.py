# Funções auxiliares
from Backend.my_blockchain import w3, sistema_cliente, PRIVATE_KEY
import requests
import qrcode
import os
import json
from PIL import Image

# CONFIGURAÇÃO CORRIGIDA
GANACHE_INITIAL_BALANCE = 200
BALANCE_TOLERANCE = 50

# Mapeamento das chaves privadas DISPONÍVEIS
GANACHE_PRIVATE_KEYS = {
    3: "0xc6ede890317519c2a17cbf1aaf24763c3373b14a5bacd9b12b429d4fa22511df",
    4: "0x21af7d9b31bb12c704f9b2794e943f55e7727676882227e2a0e1a1870db8e905",
    5: "0xfc627e2e4bce3d9e8413cb311154ccff512c1949ed035036fa4cff88fede7707",
    6: "0x440b22e6b4d83d749668fc7e18e24f1c6f9c9d080acbc87478a6167d26c522a7",
    7: "0x9b216a57c27e7768d87c8191123a40ad88a7b4cea5e8b394c5561b30aae6eb68",
    8: "0x4e42c377871aa458a1cf29d5ad47a13a8e4086b65aaa62e4a9c2bc850fc1925b",
    9: "0xe6551f303f58d910489279606532758916887bb0211a3df6fac70b8b3e5b42d4",
    10: "0x3063f3394c65b44eeca4dbb328da00e54d5fb7ef0d582f8c1c373a49e8612a5d",
    11: "0xbb458a3a02b86516aca1c5da1e38d3a0840a19aaa7ecfc85cb458164a03b92d2",
    12: "0xf55d32c3f5c627340a89ee3b997836620d1fd9eef08770d62705534e4268272a",
    13: "0x0dfd6c0be889a4c6ca773d45e036c8edeabfedcac1e1c858b7955aeea36ff84d",
    14: "0xe519b9b9c8ee1d7d80cc4b463c101a666fd6d9aa6890713741716e5b5bcb953e",
    15: "0x16e54c0ca8894085d6dc5ee3f227e48bc613a496a2cb655ddb42217a1de3c0a0",
}

ACCOUNTS_CONTROL_FILE = "accounts_control.json"


def load_accounts_control():
    """Carrega o controle de contas usadas"""
    if os.path.exists(ACCOUNTS_CONTROL_FILE):
        try:
            with open(ACCOUNTS_CONTROL_FILE, 'r') as f:
                data = json.load(f)
                return data.get('next_index', 3), data.get('used_accounts', [])
        except Exception as e:
            print(f"⚠️ Erro ao carregar controle de contas: {e}")
    return 3, []


def save_accounts_control(next_index, used_accounts):
    """Salva o controle de contas usadas"""
    try:
        data = {
            'next_index': next_index,
            'used_accounts': used_accounts
        }
        with open(ACCOUNTS_CONTROL_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Erro ao salvar controle de contas: {e}")


def reset_accounts_control():
    """Reseta o controle de contas de forma atômica"""
    try:
        temp_file = ACCOUNTS_CONTROL_FILE + ".tmp"

        # Cria estado inicial "zerado"
        data = {
            'next_index': 3,
            'used_accounts': []
        }

        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Substitui o arquivo antigo de forma atômica
        os.replace(temp_file, ACCOUNTS_CONTROL_FILE)

        # Owner do contrato (tem permissão para remover)
        owner_account = w3.eth.accounts[0]

        # Lista de contas que você quer remover
        ganache_accounts = w3.eth.accounts[3:7]  # ajuste conforme suas contas

        for cliente in ganache_accounts:
            # verifica se o cliente está registrado
            if sistema_cliente.functions.ClienteRegistrado(cliente).call():
                tx = sistema_cliente.functions.removerCliente(cliente).build_transaction({
                    'from': owner_account,
                    'gas': 200000,
                    'nonce': w3.eth.get_transaction_count(owner_account)
                })
                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                w3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"✅ Cliente {cliente} removido com sucesso")
            else:
                print(f"ℹ️ Cliente {cliente} não está registrado")

        print("✅ Controle de contas resetado com sucesso!")
        return True

    except Exception as e:
        print(f"⚠️ Erro ao resetar controle de contas: {e}")
        return False

def check_account_significantly_used(account_address):
    """
    Verifica se a conta foi significativamente usada
    CORRIGIDO: Usa 200 ETH como base e tolerância apropriada
    """
    try:
        current_balance = w3.from_wei(w3.eth.get_balance(account_address), 'ether')
        difference = abs(float(current_balance) - GANACHE_INITIAL_BALANCE)

        # Se a diferença for maior que a tolerância, considera como usada
        is_significantly_used = difference > BALANCE_TOLERANCE

        return is_significantly_used, float(current_balance), difference

    except Exception as e:
        print(f"⚠️ Erro ao verificar conta {account_address}: {e}")
        return True, 0, 0


def getGanacheAccount():
    """
    VERSÃO ATÔMICA + VERIFICAÇÃO NO CONTRATO:
    Só persiste se tudo terminar bem e pula contas já registradas no contrato
    """
    next_index, used_accounts = load_accounts_control()

    print(f"🔍 Procurando conta disponível...")
    print(f"   Chaves privadas disponíveis: {list(GANACHE_PRIVATE_KEYS.keys())}")

    available_accounts = sorted(GANACHE_PRIVATE_KEYS.keys())
    temp_used_accounts = used_accounts.copy()  # cópia em memória para atomicidade
    try:
        for account_index in available_accounts:
            if account_index >= len(w3.eth.accounts):
                print(f"   ❌ Conta {account_index} não existe no Ganache")
                continue

            account_address = w3.eth.accounts[account_index]
            private_key = GANACHE_PRIVATE_KEYS[account_index]

            if account_address in temp_used_accounts:
                print(f"   ❌ Conta {account_index} já marcada como usada")
                continue

            # 🔍 Verificação no contrato
            try:
                ja_cadastrado = sistema_cliente.functions.ClienteRegistrado(account_address).call()
                if ja_cadastrado:
                    print(f"   ❌ Conta {account_index} já cadastrada no contrato")
                    temp_used_accounts.append(account_address)
                    continue
            except Exception as e:
                print(f"⚠️ Erro ao consultar contrato para {account_address}: {e}")
                continue

            # Verificação de saldo
            is_used, current_balance, difference = check_account_significantly_used(account_address)
            if is_used:
                print(f"   ❌ Conta {account_index}: {current_balance:.6f} ETH (diferença: {difference:.6f}) - MUITO USADA")
                temp_used_accounts.append(account_address)
                continue

            # ✅ Conta disponível encontrada
            print(f"   ✅ Conta {account_index} DISPONÍVEL: {current_balance:.6f} ETH (diferença: {difference:.6f})")
            print(f"   📍 Endereço: {account_address}")
            # Marca em memória
            temp_used_accounts.append(account_address)

            # Só agora persiste no disco → atomicidade garantida
            save_accounts_control(account_index + 1, temp_used_accounts)

            return account_address, private_key

    except Exception as e:
        print(f"⚠️ Erro inesperado em getGanacheAccount: {e}")
        return None, None

    print("❌ NENHUMA CONTA DISPONÍVEL!")
    print("💡 Opções: Reinicie Ganache, rode reset_accounts_control(), ou adicione mais chaves")
    return None, None


def list_account_status_detailed():
    """Lista detalhada das contas com foco nas que têm chaves privadas"""
    next_index, used_accounts = load_accounts_control()

    print(f"\n📊 STATUS DETALHADO (Base: {GANACHE_INITIAL_BALANCE} ETH, Tolerância: {BALANCE_TOLERANCE} ETH)")
    print("=" * 100)

    # Primeiro, mostra as contas com chaves privadas (mais importantes)
    print("🔑 CONTAS COM CHAVES PRIVADAS DISPONÍVEIS:")
    available_count = 0

    for account_index in sorted(GANACHE_PRIVATE_KEYS.keys()):
        if account_index >= len(w3.eth.accounts):
            print(f"   Conta {account_index}: NÃO EXISTE NO GANACHE")
            continue

        account_address = w3.eth.accounts[account_index]
        is_used, current_balance, difference = check_account_significantly_used(account_address)
        is_in_control = account_address in used_accounts

        status_parts = []
        if is_in_control:
            status_parts.append("marcada")
        if is_used:
            status_parts.append("saldo alterado")

        if status_parts:
            status = f"USADA ({', '.join(status_parts)})"
        else:
            status = "DISPONÍVEL"
            available_count += 1

        print(
            f"   Conta {account_index:2d}: {account_address} | {current_balance:10.6f} ETH (±{difference:.6f}) | {status}")

    print(f"\n📈 RESUMO DAS CONTAS COM CHAVES:")
    print(f"   Disponíveis: {available_count}")
    print(f"   Total com chaves: {len(GANACHE_PRIVATE_KEYS)}")

    # Mostra algumas contas sem chaves (apenas informativo)
    print(f"\n🔒 PRIMEIRAS CONTAS SEM CHAVES PRIVADAS (apenas informativo):")
    for i in range(7, min(12, len(w3.eth.accounts))):  # Mostra apenas 5
        account_address = w3.eth.accounts[i]
        _, current_balance, difference = check_account_significantly_used(account_address)
        print(f"   Conta {i:2d}: {account_address} | {current_balance:10.6f} ETH (±{difference:.6f}) | SEM CHAVE")


def force_reset_with_confirmation():
    """Reset forçado com confirmação de segurança (atômico)"""
    print("🚨 RESET FORÇADO DE CONTAS")
    print("Este comando vai marcar todas as contas como disponíveis novamente.")
    print("Use APENAS se você resetou completamente o Ganache!")
    print(f"Saldo esperado após reset: {GANACHE_INITIAL_BALANCE} ETH por conta")

    print("\n📋 Status atual das contas com chaves privadas:")
    for account_index in sorted(GANACHE_PRIVATE_KEYS.keys()):
        if account_index < len(w3.eth.accounts):
            account_address = w3.eth.accounts[account_index]
            _, current_balance, difference = check_account_significantly_used(account_address)
            print(f"   Conta {account_index}: {current_balance:.6f} ETH (diferença: {difference:.6f})")

    confirmation = input(f"\nDigite 'RESET' para confirmar: ")
    if confirmation != "RESET":
        print("❌ Operação cancelada.")
        return False

    success = reset_accounts_control()
    if success:
        print("✅ Reset concluído! Teste agora:")
        print(">>> account, key = getGanacheAccount()")

    return success


def quick_test():
    """Teste rápido do sistema"""
    print("🧪 TESTE RÁPIDO DO SISTEMA")
    print("-" * 40)

    # Testa pegar uma conta
    account, private_key = getGanacheAccount()

    if account and private_key:
        print(f"✅ SUCESSO!")
        print(f"   Conta: {account}")
        print(f"   Chave: {private_key[:10]}...{private_key[-10:]}")
        return True
    else:
        print("❌ FALHOU - Nenhuma conta disponível")
        return False


# Funções mantidas (QR codes, etc.)
def gerar_qrcode(link: str, nome_arquivo: str = "qrcode.png") -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
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
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    caminho = salvar_qr(img, nome_arquivo)
    return caminho


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


def extract_interface(compiled_contracts, contract_name):
    contract_id = f"<stdin>:{contract_name}"
    interface = compiled_contracts[contract_id]
    return interface["abi"], interface["bin"]


def get_eth_to_brl():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "ethereum", "vs_currencies": "brl"}
    response = requests.get(url, params=params)
    data = response.json()
    return data["ethereum"]["brl"]


def listAllAccounts():
    print(w3.eth.accounts)
    for conta in w3.eth.accounts:
        saldo = w3.from_wei(w3.eth.get_balance(conta), 'ether')
        print(conta, saldo)


if __name__ == "__main__":
    print("🚀 SISTEMA DE CONTAS GANACHE")
    print("=" * 60)

    # Menu de opções
    print("📋 OPÇÕES DISPONÍVEIS:")
    print("1. list_account_status_detailed() - Status detalhado")
    print("2. quick_test() - Teste rápido")
    print("3. force_reset_with_confirmation() - Reset forçado")
    print("4. getGanacheAccount() - Pegar conta")

    print("\n" + "=" * 60)
    list_account_status_detailed()

    print("\n" + "=" * 60)
    print("🧪 EXECUTANDO TESTE:")
    quick_test()