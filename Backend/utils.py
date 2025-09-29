# Funções auxiliares
import base64

from Backend.my_blockchain import w3, sistema_cliente, PRIVATE_KEY
import requests
import qrcode
import os
import json
from io import BytesIO

# CONFIGURAÇÃO BASE
GANACHE_INITIAL_BALANCE = 200
BALANCE_TOLERANCE = 199

# Mapeamento das chaves privadas DISPONÍVEIS
GANACHE_PRIVATE_KEYS = {
    3: "0x78f85f6c4a0776e3c7e199327d04bc22da3551e8987e90604c17e2ac53f31dbb",
    4: "0xd914704437f070927ba9be03c7800f62cb5b759a833ad840c10f596095774ec8",
    5: "0xe05d8f69465a5a3737ec3817e2f3571e1ca6fa60e123432ce621bc3a6ba17547",
    6: "0x73811748686f728559094d29ddf4a554979fcd089ba6257add07845ef01b09f6",
    7: "0x8ca7cc3959ddf836070419ff06521dcaea7704dc383f2b53f2b131c026fcb577",
    8: "0xe5992340c28d1e354a25bf52fb9f94e7a92f45e34d9d40c0caca984853bd5267",
    9: "0x191d9a07469adacb33aed7f1ab503d1224488ef0b20f1c53a004175513930476",
    10: "0xe1702f1e5a7874f7332ff7bc819831d42728583708698ba7c24fe4e16195655a",
    11: "0x30924ab8279fcf5727fa9fc216764f2cb35ca87d72ed8aa31325d07841459a60",
    12: "0xf66d95f748d470881d370a8b35024e7e99c079c63ac02743a999b1f658249210",
    13: "0x6a6050c454ec624e07948be0571e16125b291d12eafb5a7ebda2c291415d68d0",
    14: "0x2505b899d00565b4defc4e65c7f8108343fd7b2ad36fd62fcd47079432deee64",
    15: "0x1d40d9688c1504f3b5c4aea3ef764e6a896eda1dbab6fb4f430759d4a321bd53",
    16: "0xe021083149a8c9b47bd3106b4a326e8388890070ef7a5ad491b1cb021717340a",
    17: "0x0f51b0e81773b35b6e23916ab18f722e8fdd6dcbba300f69c5b57a1d00127be5",
    18: "0x8efb899513f705e7532dd00acaa0b5cf231bcbb013e3e1c8f943f1b84df8f6f7",
    19: "0xf6f82f45818fbc2d5876b1c6e9025a048c6631c741d3ff5dfdf3f975a484cf02",
    20: "0x5aa865544e1767860c5e22dd7089f599669b1367a773b836fc45be7d637c8421",
    21: "0xc4f1661d79693b6d9a9e403eda3bc752238d6fe9cc890db4f7914d8b8c7989a5",
    22: "0xe6d1d4519d9c06e1399fe0e8c4ecbef9e7dbf9f9ba3945434212b837104eabfd",
    23: "0x98f28b015891388ae5eb86a16736a14aeff2a12bcbec5affcd511c010404ee2c",
    24: "0x3002ce861e8876ec00e1d7505c8660658178cf786bb1472d3762b587ec8e767f",
    25: "0xb9f09e4e686707e5f6858c72ffe59ae631cf648b465204f4147ae2aec6c40c75",
    26: "0xa761354493711a11bb8d991b7ce3954b2746d167060ce86ca9a95e480765992f",
    27: "0xe51c6876dc199b7d33f23375192e1b2d58ade37423ff6d0dfed91dde764135c6",
    28: "0xb97c223d75a7d9811b39fca94288de7b43949fd6e73321919cea355b75bafe3c",
    29: "0x4218d57cbc75c9dfc51e516691ea62784c0ed3a7bc337dd838664f550af564ef",
    30: "0x25801b002ace177c1982a5320042dd68adf49127eb9b907205974cf278d08f45",
    31: "0xdfdf96be8a884b0ea0c72fcfad0e6439c221063fd5cca835db1b53b07914448f",
    32: "0x5b713433befa63603d6fe1a041a35b88dfb52ede659cf66e97390ae995f3d7c9",
    33: "0xf01e57aebb6b2dab4eae484bb663d53d6e8d8695d8a1d325cf8b4d3b97617b26",
    34: "0x2d47d0b30b854a89a903f3cc5dd17de331efbb409b73a788c3bb8290801aa6ae",
    35: "0x59a7ca803e1497244d91ed233317910b4c8899ed1f5bdc0d5cf9e717387940a6",
    36: "0xa7f98aa71e957b14cb5e01a33885c070192c5e43b5fe25272e1d9ad00b513e47",
    37: "0xc246fee2a9c14f93a11d378212ea12f0275c866e67a275875f5b7f2e359cd8af",
    38: "0x56805b827a473a03119726028add5882f40ff87bc3fcf1a404e54b1d008a8f42",
    39: "0xea3aad76a5d4d3f3cf372b3dc96c16e1c9edb649188aededba60275c11c17092",
    40: "0xf1259b9115940cb81662c83c1d8195092b395e9a897b2dd79f4eaff4b42f77f0",
    41: "0xabd33b1053e3ef9861de28ba7736c0df12609c4c1f53f11428b4c0ca4dd210aa",
    42: "0x899c3b866bbefe0959b37d1cc71fdf63b03b024b1de0f28c7e936f3e3bfd51e4",
    43: "0x30e6cade82d26e4f22a99e6176b0b7c42f9808e5b2b86de8736c1f69e3069c39",
    44: "0x93d9eaa82a5f4eccb6e2e4d4efdd7562a7d8e1526272f74e8d428fe33052e38e",
    45: "0x06e93f9d024332d5918a9b56014f8ae8e654c046b5eb26db4c201498d100e9e4",
    46: "0x219e4927d0afb57464e9eeae97fbafe9f470d02a6a998f429cf5df8fca78ae5d",
    47: "0x8c3bb2a8845b82d930d2d4e100764a308536ee623faf24555f03c350f7a1797a",
    48: "0x3af4f57c110cd106fa1eddace34d79df84bad3413745530508f2216328cbd226",
    49: "0x4b12254d8b4991d74306a1009ef124ed89954b3efeefb3197400345809500aa8",
    50: "0xe70f2b0e9109508388130fce88920d4201b281cb01a4fe4710e39e6c5be4af4c"
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
        ganache_accounts = w3.eth.accounts[3:51]

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
    """
    Busca a cotação ETH/BRL com fallback robusto em duas fontes.

    Returns:
        float: Cotação ETH em BRL ou valor padrão em caso de erro.
    """
    # Valor padrão de segurança
    fallback_value = 23500.0

    # --- 1) CoinGecko ---
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "ethereum", "vs_currencies": "brl"}
        response = requests.get(url, params=params, timeout=10)

        print("➡️ URL chamada CoinGecko:", response.url)

        if response.status_code == 200:
            data = response.json()
            price = data.get("ethereum", {}).get("brl")
            if isinstance(price, (int, float)) and price > 0:
                print(f"✅ Cotação ETH/BRL obtida da CoinGecko: R$ {price:,.2f}")
                return float(price)
        else:
            print(f"❌ CoinGecko retornou status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Erro CoinGecko: {str(e)}")

    # --- 2) CryptoCompare ---
    try:
        url = "https://min-api.cryptocompare.com/data/price"
        params = {"fsym": "ETH", "tsyms": "BRL"}
        response = requests.get(url, params=params, timeout=10)

        print("➡️ URL chamada CryptoCompare:", response.url)

        if response.status_code == 200:
            data = response.json()
            price = data.get("BRL")
            if isinstance(price, (int, float)) and price > 0:
                print(f"✅ Cotação ETH/BRL obtida da CryptoCompare: R$ {price:,.2f}")
                return float(price)
        else:
            print(f"❌ CryptoCompare retornou status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Erro CryptoCompare: {str(e)}")

    # --- 3) Fallback fixo ---
    print(f"⚠️ Usando valor fallback: R$ {fallback_value:,.2f}")
    return fallback_value


def listAllAccounts():
    print(w3.eth.accounts)
    for conta in w3.eth.accounts:
        saldo = w3.from_wei(w3.eth.get_balance(conta), 'ether')
        print(conta, saldo)

def calcular_projecao(investimento_inicial_eth):

    # Projeção de 30 dias com um crescimento de 5%
    taxa_de_crescimento_mensal = 0.05
    projecao_30_dias_eth = investimento_inicial_eth * (1 + taxa_de_crescimento_mensal)

    # Projeção de 1 ano com um crescimento de 5% ao mês (composto)
    projecao_1_ano_eth = investimento_inicial_eth * (1 + taxa_de_crescimento_mensal)**12

    return {
        "projecao_30_dias_eth": projecao_30_dias_eth,
        "projecao_1_ano_eth": projecao_1_ano_eth
    }

def gerar_qr_comprovante(receipt_json, tx_id):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=4,
    )
    qr.add_data(json.dumps(receipt_json, ensure_ascii=False))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Salvar como arquivo
    pasta = "static/qrs"
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"comprovante_{tx_id}.png")
    img.save(caminho)

    # Também retornar em base64 (para front consumir diretamente)
    bio = BytesIO()
    img.save(bio, format="PNG")
    b64 = base64.b64encode(bio.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{b64}", caminho


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