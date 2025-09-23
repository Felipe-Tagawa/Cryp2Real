// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.19;

// Interface simplificada para o contrato SistemaCliente
interface ISistemaCliente {
    function ClienteRegistrado(address cliente) external view returns (bool);
    function getNomeCliente(address cliente) external view returns (string memory);
    function getEmailCliente(address cliente) external view returns (string memory);
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

    Transacao[] public transacoes;
    mapping(string => uint256) public pixParaIndiceTransacao;
    mapping(address => uint256) public transacoesPorCliente;

    // Construtor recebe o endereço do contrato SistemaCliente
    constructor(address _enderecoSistemaCliente) payable {
        require(_enderecoSistemaCliente != address(0), "Endereco do sistema cliente invalido");
        dono = msg.sender;
        contaOng = address(0);
        percentComissao = 25; // 2,5% (25/1000)
        percentOng = 25; // 2,5% (25/1000)
        clientes = ISistemaCliente(_enderecoSistemaCliente);
    }

    function saldoContrato() public view returns (uint256) {
        return address(this).balance;
    }

    function saldoOng() public view returns (uint256) {
        if (contaOng == address(0)) {
            return 0;
        }
        return address(contaOng).balance;
    }

    // Pagamento para comerciante usando ETH direto (sem saldo interno)
    function realizaPagamentoCliente(
        uint256 valor,
        string memory referenciaPix,
        address payable clienteDestino
    ) public payable noReentrance apenasClienteRegistrado {
        require(msg.value > 0, "Valor ETH deve ser maior que zero");
        require(msg.value >= valor, "ETH enviado insuficiente");
        require(clienteDestino != address(0), "Endereco cliente destino invalido");
        require(bytes(referenciaPix).length > 0, "Referencia PIX invalida");

        uint256 valorComissao = (valor * percentComissao) / 1000;
        uint256 valorParaOng = (valor * percentOng) / 1000;
        uint256 valorCliente = valor - valorComissao - valorParaOng;

        require(valorCliente > 0, "Valor liquido deve ser maior que zero");

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

        // Realizar transferências usando ETH enviado
        (bool successComissao,) = payable(dono).call{value: valorComissao}("");
        require(successComissao, "Falha na transferencia da comissao");

        if (contaOng != address(0) && valorParaOng > 0) {
            (bool successOng,) = payable(contaOng).call{value: valorParaOng}("");
            require(successOng, "Falha na transferencia para ONG");
        }

        (bool successCliente,) = clienteDestino.call{value: valorCliente}("");
        require(successCliente, "Falha na transferencia para cliente");

        // Retornar o troco se houver
        uint256 troco = msg.value - valor;
        if (troco > 0) {
            (bool successTroco,) = payable(msg.sender).call{value: troco}("");
            require(successTroco, "Falha ao retornar troco");
        }

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

    // Transferência P2P com taxas usando ETH direto
    function transferirETHDireto(
        string memory referenciaPix,
        address payable usuarioDestino
    ) public payable noReentrance apenasClienteRegistrado {
        require(usuarioDestino != address(0), "Endereco destino invalido");
        require(usuarioDestino != msg.sender, "Nao pode transferir para si mesmo");
        require(msg.value > 0, "Valor deve ser maior que zero");
        require(bytes(referenciaPix).length > 0, "Referencia PIX invalida");
        require(clientes.ClienteRegistrado(usuarioDestino), "Usuario destino nao registrado");

        uint256 valorTotal = msg.value;

        // Calcular taxas
        uint256 valorComissao = (valorTotal * percentComissao) / 1000;
        uint256 valorParaOng = (valorTotal * percentOng) / 1000;
        uint256 valorLiquido = valorTotal - valorComissao - valorParaOng;

        require(valorLiquido > 0, "Valor liquido deve ser maior que zero");

        transacoesPorCliente[usuarioDestino]++;

        string memory nomeCliente = clientes.getNomeCliente(msg.sender);
        string memory emailCliente = clientes.getEmailCliente(msg.sender);

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

        // Realizar as transferências usando call
        (bool successComissao,) = payable(dono).call{value: valorComissao}("");
        require(successComissao, "Falha na transferencia da comissao");

        if (contaOng != address(0) && valorParaOng > 0) {
            (bool successOng,) = payable(contaOng).call{value: valorParaOng}("");
            require(successOng, "Falha na transferencia para ONG");
        }

        (bool successDestino,) = usuarioDestino.call{value: valorLiquido}("");
        require(successDestino, "Falha na transferencia para usuario destino");

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

    // Transferência simples sem taxas (P2P puro) - MODIFICADA PARA NÃO DEPENDER DE REGISTRO
    function transferenciaSemTaxas(
        string memory referenciaPix,
        address payable usuarioDestino
    ) public payable noReentrance {
        require(usuarioDestino != address(0), "Endereco destino invalido");
        require(usuarioDestino != msg.sender, "Nao pode transferir para si mesmo");
        require(msg.value > 0, "Valor deve ser maior que zero");
        require(bytes(referenciaPix).length > 0, "Referencia PIX invalida");

        transacoesPorCliente[usuarioDestino]++;

        // Usar valores padrão se o cliente não estiver registrado
        string memory nomeCliente = "Usuario nao registrado";
        string memory emailCliente = "nao-informado@exemplo.com";

        if (address(clientes) != address(0) && clientes.ClienteRegistrado(msg.sender)) {
            nomeCliente = clientes.getNomeCliente(msg.sender);
            emailCliente = clientes.getEmailCliente(msg.sender);
        }

        Transacao memory novaTransacao = Transacao({
            clienteDestino: usuarioDestino,
            pagador: msg.sender,
            valorTotal: msg.value,
            valorCliente: msg.value,
            valorComissao: 0,
            valorParaOng: 0,
            timestamp: block.timestamp,
            referenciaPix: referenciaPix,
            nomeCliente: nomeCliente,
            emailCliente: emailCliente
        });

        transacoes.push(novaTransacao);
        pixParaIndiceTransacao[referenciaPix] = transacoes.length - 1;

        (bool success,) = usuarioDestino.call{value: msg.value}("");
        require(success, "Falha na transferencia para usuario destino");

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

    // Função de saldo interno removida - agora só consulta saldo ETH real
    function consultarSaldoETH(address cliente) public view returns (uint256) {
        return cliente.balance;
    }

    function acessoTransacao(string memory referenciaPix)
        public
        view
        onlyDono
        returns (Transacao memory)
    {
        require(bytes(referenciaPix).length > 0, "Referencia PIX invalida");
        require(pixParaIndiceTransacao[referenciaPix] < transacoes.length, "Transacao nao encontrada");
        return transacoes[pixParaIndiceTransacao[referenciaPix]];
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
            valorComissao = (valorComissao - (valorComissao * 10) / 100);
            valorOng = (valorOng + (valorOng * 3) / 100);
        } else {
            valorComissao = (valorComissao - (valorComissao * 15) / 100);
            valorOng = (valorOng + (valorOng * 5) / 100);
        }

        return (valorComissao, valorOng);
    }

    // Função para configurar ou alterar a ONG
    function setContaOng(address _contaOng) external onlyDono {
        require(_contaOng != address(0), "Endereco da ONG invalido");
        contaOng = _contaOng;
        emit mudarContaOng(_contaOng);
    }

    // Doação direta usando ETH enviado
    function doacaoDireta() public payable noReentrance {
        require(msg.value > 0, "Voce deve enviar um valor maior do que zero");
        require(contaOng != address(0), "Conta da ONG nao configurada");

        string memory nomeDoador = "Doador anonimo";
        string memory emailDoador = "anonimo@exemplo.com";

        if (address(clientes) != address(0) && clientes.ClienteRegistrado(msg.sender)) {
            nomeDoador = clientes.getNomeCliente(msg.sender);
            emailDoador = clientes.getEmailCliente(msg.sender);
        }

        (bool success,) = payable(contaOng).call{value: msg.value}("");
        require(success, "Falha na transferencia da doacao");

        emit doacaoRealizada(msg.sender, msg.value, nomeDoador, emailDoador);
    }

    // Função para permitir recebimento de ETH diretamente no contrato
    receive() external payable {}
    fallback() external payable {}
}