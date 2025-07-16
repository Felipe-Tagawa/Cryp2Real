
# 🚀 Sistema de Pagamento Blockchain

Um sistema completo de pagamentos descentralizado construído com Ethereum, Flask e Web3.py, permitindo transações seguras entre clientes e comerciantes com suporte a conversão BRL/ETH.

## ✨ Funcionalidades

### 🔐 Gestão de Clientes
- **Registro de usuários** com criação automática de carteiras Ethereum
- **Autenticação segura** com hash de senhas
- **Gerenciamento de saldo** em ETH com conversão para BRL em tempo real
- **Referências PIX** para identificação única de usuários

### 💳 Sistema de Pagamentos
- **Pagamentos instantâneos** entre clientes e comerciantes
- **Conversão automática** BRL → ETH para facilitar transações
- **Sistema de comissões** configurável para sustentabilidade da plataforma
- **Doações diretas** para ONGs parceiras

### 📊 Monitoramento e Controle
- **Histórico completo** de todas as transações
- **Consulta de saldos** em tempo real
- **Sistema de bônus** baseado no volume de transações
- **Dashboard administrativo** para gerenciamento da plataforma

## 🏗️ Arquitetura do Sistema

### Backend API (Flask)
```
📂 API Flask
├── 🔗 Integração Web3.py
├── 💱 Conversão de moedas (BRL/ETH)
├── 🔐 Gestão de carteiras
└── 📡 Endpoints RESTful
```

### Smart Contracts (Solidity)
```
📂 Contratos Inteligentes
├── 👥 SistemaCliente.sol - Gestão de usuários
├── 💰 NewEther.sol - Processamento de pagamentos
└── 🔗 Interface de comunicação entre contratos
```

### Blockchain Infrastructure
```
📂 Infraestrutura
├── 🌐 Ganache (Desenvolvimento)
├── 🗄️ MySQL (Dados auxiliares)
└── 🔗 Web3.py (Integração Python-Ethereum)
```

## 🛠️ Tecnologias Utilizadas

| Categoria | Tecnologia | Versão | Descrição |
|-----------|------------|---------|-----------|
| **Backend** | Flask | 2.x | Framework web Python |
| **Blockchain** | Solidity | ^0.8.19 | Linguagem para smart contracts |
| **Integração** | Web3.py | 6.x | Biblioteca Python para Ethereum |
| **Desenvolvimento** | Ganache | 7.x | Blockchain local para testes |
| **Banco de Dados** | MySQL | 8.x | Armazenamento de dados auxiliares |
| **Criptografia** | eth-account | 0.8.x | Gerenciamento de contas Ethereum |

## 📋 Pré-requisitos

- Python 3.8+
- Node.js 16+
- MySQL 8.0+
- Ganache CLI ou GUI

## 🚀 Instalação e Configuração

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/blockchain-payment-system.git
cd blockchain-payment-system
```

### 2. Instale as dependências Python
```bash
pip install -r requirements.txt
```

### 3. Configure o ambiente
```bash
# Crie um arquivo .env na raiz do projeto
cp .env.example .env
```

### 4. Configure o MySQL
```sql
CREATE DATABASE blockchain_payments;
-- Execute os scripts SQL de criação das tabelas
```

### 5. Inicie o Ganache
```bash
# Via CLI
ganache-cli --deterministic --accounts 10 --host 0.0.0.0 --port 8545

# Ou use o Ganache GUI
```

### 6. Deploy dos contratos
```bash
python deploy_contract.py
```

### 7. Inicie a aplicação
```bash
python app.py
```

## 📚 Endpoints da API

### 👥 Gestão de Clientes

#### `POST /registrarCliente`
Registra um novo cliente no sistema
```json
{
  "nome": "João Silva",
  "referenciaPix": "joao@email.com",
  "email": "joao@email.com",
  "senha": "minhasenha123"
}
```

#### `GET /mostraInfoCliente?carteira=0x...`
Retorna informações detalhadas do cliente
```json
{
  "nome": "João Silva",
  "email": "joao@email.com",
  "referenciaPix": "joao@email.com",
  "saldo": {
    "wei": "1000000000000000000",
    "eth": "1.0",
    "reais": 18000.00
  },
  "cotacao_eth_brl": 18000.00
}
```

### 💰 Operações Financeiras

#### `POST /adicionaSaldo`
Adiciona saldo à conta do cliente
```json
{
  "carteira": "0x742d35Cc6634C0532925a3b8D404D0C18b5a4b2F",
  "valor_reais": 100.00
}
```

#### `POST /realizaPagamento`
Processa pagamento entre cliente e comerciante
```json
{
  "valor_reais": 50.00,
  "referenciaPix": "joao@email.com",
  "comerciante": "0x8ba1f109551bD432803012645Hac136c9c66fbbf"
}
```

#### `GET /saldoComerciante`
Consulta saldo do comerciante
```json
{
  "saldo_wei": "2000000000000000000",
  "saldo_eth": "2.000000",
  "saldo_reais": "36000.00"
}
```

## 🔒 Segurança

### Smart Contracts
- **Modifier de reentrância** para prevenir ataques
- **Validação de endereços** em todas as transações
- **Controle de acesso** baseado em roles
- **Hash seguro de senhas** com salt baseado no endereço

### API
- **Validação rigorosa** de todos os inputs
- **Tratamento de erros** abrangente
- **Logging** de todas as operações sensíveis
- **Rate limiting** para prevenir spam

## 🎯 Fluxo de Pagamento

```mermaid
graph TD
    A[Cliente solicita pagamento] --> B[Validação de dados]
    B --> C[Verificação de saldo]
    C --> D[Cálculo de comissões]
    D --> E[Atualização de saldo do cliente]
    E --> F[Transferência para comerciante]
    F --> G[Transferência de comissão]
    G --> H[Transferência para ONG]
    H --> I[Registro da transação]
    I --> J[Emissão de eventos]
```

## 🔧 Configuração de Desenvolvimento

### Estrutura de Pastas
```
projeto/
├── app.py                 # Aplicação Flask principal
├── blockchain.py          # Configurações Web3
├── utils.py              # Funções utilitárias
├── deploy_contract.py    # Deploy dos contratos
├── contracts/
│   ├── SistemaCliente.sol
│   └── NewEther.sol
├── migrations/           # Scripts de migração do BD
└── tests/               # Testes automatizados
```

### Variáveis de Ambiente
```env
# Blockchain
GANACHE_URL=http://127.0.0.1:8545
PRIVATE_KEY=0x...
MERCHANT_ADDRESS=0x...

# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=blockchain_payments

# API
FLASK_ENV=development
FLASK_DEBUG=True
API_BASE_URL=http://localhost:5000
```

## 📈 Monitoramento e Logs

### Eventos do Smart Contract
- `novoClienteRegistrado`: Novo cliente cadastrado
- `PagamentoRecebido`: Pagamento processado com sucesso
- `doacaoRealizada`: Doação efetuada para ONG

### Métricas Importantes
- Volume total de transações
- Valor médio por transação
- Taxa de conversão BRL/ETH
- Comissões arrecadadas

---

👥 Equipe de Desenvolvimento
Este projeto foi desenvolvido por:

Felipe Silva Loschi - Integração Blockchain e FlutterFlow

Felipe Tagawa Reis - Desenvolvimento Backend e Smart Contracts

Pedro Henrique Ribeiro Dias - Arquitetura do Sistema e Banco de Dados
