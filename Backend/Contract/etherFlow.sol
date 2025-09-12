// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.19;

// Interface para o contrato SistemaCliente (conexão de contratos)
interface ISistemaCliente {
    function ClienteRegistrado(address cliente) external view returns (bool);
    function getNomeCliente(address cliente) external view returns (string memory);
    function getEmailCliente(address cliente) external view returns (string memory);
    function saldoCliente(address cliente) external view returns (uint256);
    function atualizarSaldoCliente(address cliente, uint256 novoSaldo) external;
}

contract etherFlow {
    address public dono;
    address public contaOng;
    uint256 public percentComissao;
    uint256 public percentOng;
    bool private bloqueio;
    ISistemaCliente public clientes; // Interface para o contrato de clientes

    modifier noReentrance() {
        require(!bloqueio, "Reentrancia registrada!");
        bloqueio = true;
        _;
        bloqueio = false;
    }

    modifier apenasClienteRegistrado() {
        require(clientes.ClienteRegistrado(msg.sender), "Cliente nao registrado!");
        _;
    }

    modifier onlyDono() {
        require(msg.sender == dono, "Apenas o dono pode executar esta acao");
        _;
    }

    struct Transacao {
        address clienteDestino;
        address pagador;
        uint256 valorTotal;
        uint256 valorCliente;
        uint256 valorComissao;
        uint256 valorParaOng;
        uint256 timestamp;
        string referenciaPix;
        string nomeCliente;
        string emailCliente;
    }

    event PagamentoRecebido(
        address clienteDestino,
        address pagador,
        uint256 valorTotal,
        uint256 valorCliente,
        uint256 valorComissao,
        uint256 valorParaOng,
        uint256 timestamp,
        string referenciaPix,
        string nomeCliente,
        string emailCliente
    );

    event pagamentoRealizado(
        address indexed carteira,
        uint256 valor,
        string referenciaPix
    );

    event mudarContaOng(address novaContaOrg);
    event mudarComissaoFinal(uint256 novaComissaoDono, uint256 novaComissaoOng);
    event doacaoRealizada(address doador, uint256 valor, string nomeDoador, string emailDoador);

    // Construtor recebe o endereço do contrato SistemaCliente
    constructor(address _enderecoSistemaCliente) payable {
        dono = msg.sender;
        contaOng = address(0);
        percentComissao = 25; // 2,5% (25/1000)
        percentOng = 25; // 2,5% (25/1000)
        clientes = ISistemaCliente(_enderecoSistemaCliente);
    }

    function saldoContrato() public view returns (uint256) {
        return address(this).balance;
    }

    function saldoCliente() public view apenasClienteRegistrado returns (uint256) {
        return clientes.saldoCliente(msg.sender);
    }

    function saldoOng() public view returns (uint256) {
        return address(contaOng).balance;
    }

    Transacao[] public transacoes;
    mapping(string => uint256) public pixParaIndiceTransacao;
    mapping(address => uint256) public transacoesPorCliente;

    function realizaPagamentoCliente(
        uint256 valor,
        string memory referenciaPix,
        address payable clienteDestino // Trocar para o endereço do cliente destino
    ) public payable noReentrance apenasClienteRegistrado {

        uint256 saldoAtual = clientes.saldoCliente(msg.sender);
        require(saldoAtual >= valor, "Saldo insuficiente.");

        uint256 novoSaldo = saldoAtual - valor;
        clientes.atualizarSaldoCliente(msg.sender, novoSaldo);

        uint256 valorComissao = (valor * percentComissao) / 1000;
        uint256 valorParaOng = (valor * percentOng) / 1000;
        uint256 valorCliente = valor - valorComissao - valorParaOng;

        transacoesPorCliente[clienteDestino]++;

        string memory nomeCliente = clientes.getNomeCliente(msg.sender);
        string memory emailCliente = clientes.getEmailCliente(msg.sender);

        Transacao memory novaTransacao = Transacao({
            clienteDestino: clienteDestino,
            pagador: msg.sender,
            valorTotal: valor,
            valorCliente: valorCliente,
            valorComissao: valorComissao,
            valorParaOng: valorParaOng,
            timestamp: block.timestamp,
            referenciaPix: referenciaPix,
            nomeCliente: nomeCliente,
            emailCliente: emailCliente
        });

        transacoes.push(novaTransacao);
        pixParaIndiceTransacao[referenciaPix] = transacoes.length - 1;

        payable(dono).transfer(valorComissao);
        if (contaOng != address(0)) {
            payable(contaOng).transfer(valorParaOng);
        }
        clienteDestino.transfer(valorCliente); // Erro provavel

        emit PagamentoRecebido(
            clienteDestino,
            msg.sender,
            valor,
            valorCliente,
            valorComissao,
            valorParaOng,
            block.timestamp,
            referenciaPix,
            nomeCliente,
            emailCliente
        );

        emit pagamentoRealizado(msg.sender, valor, referenciaPix);
    }

    //Transferência P2P entre usuários
    function transferirParaUsuario(
        uint256 valor,
        string memory referenciaPix,
        address payable usuarioDestino
        ) public payable noReentrance apenasClienteRegistrado {

        require(usuarioDestino != address(0), "Endereco destino invalido");
        require(usuarioDestino != msg.sender, "Nao pode transferir para si mesmo");
        require(valor > 0, "Valor deve ser maior que zero");

        // Verificar se o usuário destino está registrado no sistema
        require(clientes.ClienteRegistrado(usuarioDestino), "Usuario destino nao registrado");

        // OPÇÃO 1: Sistema baseado em saldo interno do contrato
        // Usar quando os usuários depositam ETH no contrato e mantêm saldo interno
        uint256 saldoAtual = clientes.saldoCliente(msg.sender);
        require(saldoAtual >= valor, "Saldo insuficiente");

        // Calcular taxas
        uint256 valorComissao = (valor * percentComissao) / 1000;
        uint256 valorParaOng = (valor * percentOng) / 1000;
        uint256 valorLiquido = valor - valorComissao - valorParaOng;

        // Atualizar saldos internos
        uint256 novoSaldoOrigem = saldoAtual - valor;
        uint256 saldoDestinoAtual = clientes.saldoCliente(usuarioDestino);
        uint256 novoSaldoDestino = saldoDestinoAtual + valorLiquido;

        clientes.atualizarSaldoCliente(msg.sender, novoSaldoOrigem);
        clientes.atualizarSaldoCliente(usuarioDestino, novoSaldoDestino);

        // Incrementar contador de transações
        transacoesPorCliente[usuarioDestino]++;

        // Obter dados do cliente para registro
        string memory nomeCliente = clientes.getNomeCliente(msg.sender);
        string memory emailCliente = clientes.getEmailCliente(msg.sender);

        // Criar registro da transação
        Transacao memory novaTransacao = Transacao({
            clienteDestino: usuarioDestino,
            pagador: msg.sender,
            valorTotal: valor,
            valorCliente: valorLiquido,
            valorComissao: valorComissao,
            valorParaOng: valorParaOng,
            timestamp: block.timestamp,
            referenciaPix: referenciaPix,
            nomeCliente: nomeCliente,
            emailCliente: emailCliente
        });

        transacoes.push(novaTransacao);
        pixParaIndiceTransacao[referenciaPix] = transacoes.length - 1;

        // Transferir taxas para destinatários (do pool do contrato)
        payable(dono).transfer(valorComissao);
        if (contaOng != address(0) && valorParaOng > 0) {
            payable(contaOng).transfer(valorParaOng);
        }

        emit PagamentoRecebido(
            usuarioDestino,
            msg.sender,
            valor,
            valorLiquido,
            valorComissao,
            valorParaOng,
            block.timestamp,
            referenciaPix,
            nomeCliente,
            emailCliente
        );

        emit pagamentoRealizado(msg.sender, valor, referenciaPix);
    }

    // OPÇÃO 2: Sistema de transferência direta de ETH (sem saldo interno)
    function transferirETHDireto(
        string memory referenciaPix,
        address payable usuarioDestino
        ) public payable noReentrance apenasClienteRegistrado {

        require(usuarioDestino != address(0), "Endereco destino invalido");
        require(usuarioDestino != msg.sender, "Nao pode transferir para si mesmo");
        require(msg.value > 0, "Valor deve ser maior que zero");

        // Verificar se o usuário destino está registrado
        require(clientes.ClienteRegistrado(usuarioDestino), "Usuario destino nao registrado");

        uint256 valorTotal = msg.value;

        // Calcular taxas
        uint256 valorComissao = (valorTotal * percentComissao) / 1000;
        uint256 valorParaOng = (valorTotal * percentOng) / 1000;
        uint256 valorLiquido = valorTotal - valorComissao - valorParaOng;

        require(valorLiquido > 0, "Valor liquido deve ser maior que zero");

        // Incrementar contador de transações
        transacoesPorCliente[usuarioDestino]++;

        // Obter dados do cliente
        string memory nomeCliente = clientes.getNomeCliente(msg.sender);
        string memory emailCliente = clientes.getEmailCliente(msg.sender);

        // Criar registro da transação
        Transacao memory novaTransacao = Transacao({
            clienteDestino: usuarioDestino,
            pagador: msg.sender,
            valorTotal: valorTotal,
            valorCliente: valorLiquido,
            valorComissao: valorComissao,
            valorParaOng: valorParaOng,
            timestamp: block.timestamp,
            referenciaPix: referenciaPix,
            nomeCliente: nomeCliente,
            emailCliente: emailCliente
        });

        transacoes.push(novaTransacao);
        pixParaIndiceTransacao[referenciaPix] = transacoes.length - 1;

        // Realizar as transferências
        payable(dono).transfer(valorComissao);

        if (contaOng != address(0) && valorParaOng > 0) {
            payable(contaOng).transfer(valorParaOng);
        }

        // Transferir valor líquido para o usuário destino
        usuarioDestino.transfer(valorLiquido);

        emit PagamentoRecebido(
            usuarioDestino,
            msg.sender,
            valorTotal,
            valorLiquido,
            valorComissao,
            valorParaOng,
            block.timestamp,
            referenciaPix,
            nomeCliente,
            emailCliente
        );

        emit pagamentoRealizado(msg.sender, valorTotal, referenciaPix);
    }

    // OPÇÃO 3: Transferência simples sem taxas (P2P puro)
    function transferenciaSemTaxas(
        string memory referenciaPix,
        address payable usuarioDestino
        ) public payable noReentrance apenasClienteRegistrado {

        require(usuarioDestino != address(0), "Endereco destino invalido");
        require(usuarioDestino != msg.sender, "Nao pode transferir para si mesmo");
        require(msg.value > 0, "Valor deve ser maior que zero");

        // Verificar se o usuário destino está registrado
        require(clientes.ClienteRegistrado(usuarioDestino), "Usuario destino nao registrado");

        // Incrementar contador de transações
        transacoesPorCliente[usuarioDestino]++;

        // Obter dados do cliente
        string memory nomeCliente = clientes.getNomeCliente(msg.sender);
        string memory emailCliente = clientes.getEmailCliente(msg.sender);

        // Criar registro da transação (sem taxas)
        Transacao memory novaTransacao = Transacao({
            clienteDestino: usuarioDestino,
            pagador: msg.sender,
            valorTotal: msg.value,
            valorCliente: msg.value, // Valor total vai para o destinatário
            valorComissao: 0,
            valorParaOng: 0,
            timestamp: block.timestamp,
            referenciaPix: referenciaPix,
            nomeCliente: nomeCliente,
            emailCliente: emailCliente
        });

        transacoes.push(novaTransacao);
        pixParaIndiceTransacao[referenciaPix] = transacoes.length - 1;

        // Transferir todo o valor para o destinatário
        usuarioDestino.transfer(msg.value);

        emit PagamentoRecebido(
            usuarioDestino,
            msg.sender,
            msg.value,
            msg.value,
            0,
            0,
            block.timestamp,
            referenciaPix,
            nomeCliente,
            emailCliente
        );

        emit pagamentoRealizado(msg.sender, msg.value, referenciaPix);
    }

    // Função auxiliar para verificar saldo interno (se usando OPÇÃO 1)
    function consultarSaldoInterno(address cliente) public view returns (uint256) {
        return clientes.saldoCliente(cliente);
    }

    // Função auxiliar para verificar saldo real ETH na wallet
    function consultarSaldoETH(address cliente) public view returns (uint256) {
        return cliente.balance;
    }



    function acessoTransacao(string memory referenciaPix)
        public
        view
        onlyDono
        returns (Transacao memory)
    {
        require(
            pixParaIndiceTransacao[referenciaPix] < transacoes.length,
            "Transacao nao encontrada"
        );
        return transacoes[pixParaIndiceTransacao[referenciaPix]];
    }

    function setNovaOng(address _contaOng) public onlyDono {
        require(_contaOng != address(0), "Endereco da ONG invalido!");
        contaOng = _contaOng;
        emit mudarContaOng(contaOng);
    }

    function setNovaComissao(uint256 _novaComissaoDono, uint256 _novaComissaoOng) public onlyDono {
        percentComissao = _novaComissaoDono;
        percentOng = _novaComissaoOng;
        emit mudarComissaoFinal(_novaComissaoDono, _novaComissaoOng);
    }

    function getNumeroTransacoes(address clienteDestino) public view returns (uint256) {
        return transacoesPorCliente[clienteDestino];
    }

    function obterBonusPorTransacoes(address clienteDestino)
        public
        view
        returns (uint256, uint256)
    {
        uint256 numTransacoes = getNumeroTransacoes(clienteDestino);
        uint256 valorComissao = percentComissao;
        uint256 valorOng = percentOng;

        if (numTransacoes == 0) {
            valorComissao = percentComissao;
            valorOng = percentOng;
        } else if (numTransacoes >= 1 && numTransacoes <= 4) {
            valorComissao = (valorComissao - (valorComissao * 5) / 100);
            valorOng = (valorOng + (valorOng * 2) / 100);
        } else if (numTransacoes > 4 && numTransacoes <= 10) {
            valorComissao = (valorComissao - (valorComissao * 1) / 10);
            valorOng = (valorOng + (valorOng * 3) / 100);
        } else {
            valorComissao = (valorComissao - (valorComissao * 15) / 1000);
            valorOng = (valorOng + (valorOng * 5) / 100);
        }

        return (valorComissao, valorOng);
    }

    function doacaoDireta() public payable noReentrance apenasClienteRegistrado {
        require(msg.value > 0, "Voce deve enviar um valor maior do que zero");

        uint256 valorDoado = msg.value;
        uint256 saldoAtual = clientes.saldoCliente(msg.sender);
        require(saldoAtual >= valorDoado, "Saldo insuficiente para doacao.");

        // Atualizar saldo do cliente
        uint256 novoSaldo = saldoAtual - valorDoado;
        clientes.atualizarSaldoCliente(msg.sender, novoSaldo);

        // Dados do doador
        string memory nomeDoador = "";
        string memory emailDoador = "";

        if (clientes.ClienteRegistrado(msg.sender)) {
            nomeDoador = clientes.getNomeCliente(msg.sender);
            emailDoador = clientes.getEmailCliente(msg.sender);
        }

        // Transferir para a ONG
        if (contaOng != address(0)) {
            payable(contaOng).transfer(valorDoado);
        }

        emit doacaoRealizada(msg.sender, valorDoado, nomeDoador, emailDoador);
    }
}