# Funções auxiliares
from Backend.my_blockchain import w3, sistema_cliente, PRIVATE_KEY
import requests
import qrcode
import os
import json
from PIL import Image

# CONFIGURAÇÃO BASE
GANACHE_INITIAL_BALANCE = 200
BALANCE_TOLERANCE = 50

# Mapeamento das chaves privadas DISPONÍVEIS
GANACHE_PRIVATE_KEYS = {
    3: "0x17955ca81ffdbf3f19eff23a95f052a3de3078aee2bdb021697ba43e205f8315",
    4: "0xedac0eb30988b13c9b9f23499d9dc631182ca54c61116e06dc6581eb166b1c7b",
    5: "0xfb43c746bd917f896cad406c650ce8d9584e292f0def92d0bd2fb175f5af0baf",
    6: "0x01bbc71b2b68d89c6c0af6032d87a68b6126624fb28e7d43037588a4e583b26c",
    7: "0x23abee6eb0f97b149c5527b730065278e3485b3f81fd06b161115f94d1174978",
    8: "0x29b98f622877f0e263e39543489bad9e2f9c108d183a6b60bb414d9991e866e9",
    9: "0x49ed7fe68774ff7474f730ec259e56957445cd7ceac2af3485dcecd551510f3b",
    10: "0xef3a4dfbc7ef336e6b51eb5cc4cd76724517e5d34255bbcc35b72993b01a4b4c",
    11: "0x56da96aa8d7f91407ebd103b9afb9261297cc7716e8db7a7f420a93133ebc630",
    12: "0x764f964abfe171a3a5f3077293500b738df159b24316aebc252ee6cded4e9716",
    13: "0xb6af242377ef688ceb07366416f4220fa89d2779a43cb04b21818510a06e0a53",
    14: "0x2945d4bfd655e04cf2cc000e4620d2eb126438837deaa0ae4c2949ea592f0cf4",
    15: "0x336d8fbbbbecbf8039a205b209ed488835109a5a26fc035dab59be53feb7bbd6",
    16: "0xde4abe4b135ce77ced239df1d7797595b1cee1b23dfe24dfe9ef10e491a79ae5",
    17: "0x3904f9aa43ecf8740cb5bed7c9218219399b6c3a70282f2ea47e5344340ff533",
    18: "0xcc6dc67ac4293f39589d569f4de218e790173f45a404f33b374a212ae70d1903",
    19: "0xa9697b132dd04ceae4313e99648a9e0344a8bb201e5d74d92887f88a06c77f32",
    20: "0x4f780be88812e1d1c05759afc24f31171a2e3457d332a722da8e88905850f4da"
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
        ganache_accounts = w3.eth.accounts[3:21]

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

    next_index, used_accounts = load_accounts_control()
    print(f"🔍 Procurando conta disponível (DEBUG)...")
    print(f"   Próximo índice no controle: {next_index}")
    print(f"   Contas já usadas: {used_accounts}")

    available_accounts = sorted(GANACHE_PRIVATE_KEYS.keys())
    temp_used_accounts = used_accounts.copy()

    for account_index in available_accounts:
        if account_index >= len(w3.eth.accounts):
            print(f"   ❌ Conta {account_index} não existe no Ganache")
            continue

        account_address = w3.eth.accounts[account_index]
        private_key = GANACHE_PRIVATE_KEYS[account_index]

        print(f"\n📌 Testando conta {account_index} -> {account_address}")

        if account_address in temp_used_accounts:
            print(f"   ❌ Conta já marcada como usada no controle")
            continue

        # 🔍 Verificação no contrato
        try:
            ja_cadastrado = sistema_cliente.functions.ClienteRegistrado(account_address).call()
            print(f"   - Cliente registrado no contrato? {ja_cadastrado}")
            if ja_cadastrado:
                temp_used_accounts.append(account_address)
                continue
        except Exception as e:
            print(f"⚠️ Erro ao consultar contrato para {account_address}: {e}")
            continue

        # Verificação de saldo
        is_used, current_balance, difference = check_account_significantly_used(account_address)
        print(f"   - Saldo atual: {current_balance:.6f} ETH, diferença: {difference:.6f}, usado? {is_used}")
        if is_used:
            temp_used_accounts.append(account_address)
            continue

        # ✅ Conta disponível encontrada
        print(f"   ✅ Conta DISPONÍVEL! Marcando como usada e salvando controle")
        temp_used_accounts.append(account_address)
        save_accounts_control(account_index + 1, temp_used_accounts)
        return account_address, private_key

    print("❌ NENHUMA CONTA DISPONÍVEL!")
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