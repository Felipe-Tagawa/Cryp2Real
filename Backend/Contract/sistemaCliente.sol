pragma solidity ^0.8.19;

contract SistemaCliente {
    address public dono;

    struct Cliente {
        address carteira;
        string nome;
        bool registrado;
        string referenciaPix;
        string email;
        bytes32 senhaHash;
    }

    // Endereço => dados do cliente
    mapping(address => Cliente) public clientes;

    // referenciaPix => endereço
    mapping(string => address) public pixCliente;

    // email => endereço
    mapping(string => address) public emailCliente;

    // ========== Eventos ==========
    event novoClienteRegistrado(
        address indexed carteira,
        string indexed nome,
        string referenciaPix,
        string email
    );

    event clienteAutenticado(
        address indexed carteira,
        string email,
        uint256 timestamp
    );

    event TransferenciaETH(
        address indexed origem,
        address indexed destino,
        uint256 valor
    );

    // ========== Modifiers ==========
    modifier apenasClienteRegistrado() {
        require(clientes[msg.sender].registrado, "Cliente nao registrado!");
        _;
    }

    modifier apenasDono() {
        require(msg.sender == dono, "Apenas o dono pode executar");
        _;
    }

    constructor() {
        dono = msg.sender;
    }

    // ========== Utilitarios ==========
    function gerarHashSenha(string memory senha, address salt)
        private
        pure
        returns (bytes32)
    {
        return keccak256(abi.encodePacked(senha, salt));
    }

    // ========== Registro / Autenticacao ==========
    function registrarCliente(
        string memory nome,
        string memory _referenciaPix,
        string memory email,
        string memory senha
    ) public {
        // referencias e emails devem ser unicos
        require(pixCliente[_referenciaPix] == address(0), "Referencia PIX ja esta em uso!");
        require(emailCliente[email] == address(0), "Email ja esta em uso!");
        require(!clientes[msg.sender].registrado, "Este endereco ja possui um cliente!");
        require(bytes(_referenciaPix).length > 0, "Referencia PIX invalida!");
        require(bytes(email).length > 0, "Email invalido!");
        require(bytes(senha).length >= 6, "Senha deve ter pelo menos 6 caracteres!");

        bytes32 senhaHash = gerarHashSenha(senha, msg.sender);

        clientes[msg.sender] = Cliente({
            carteira: msg.sender,
            nome: nome,
            registrado: true,
            referenciaPix: _referenciaPix,
            email: email,
            senhaHash: senhaHash
        });

        // unificado
        pixCliente[_referenciaPix] = msg.sender;
        emailCliente[email] = msg.sender;

        emit novoClienteRegistrado(msg.sender, nome, _referenciaPix, email);
    }

    function autenticarCliente(string memory email, string memory senha)
        public
        view
        returns (bool, address)
    {
        address clienteAddress = emailCliente[email];
        require(clienteAddress != address(0), "Email nao encontrado!");

        Cliente memory cliente = clientes[clienteAddress];
        require(cliente.registrado, "Cliente nao registrado!");

        bytes32 senhaHash = gerarHashSenha(senha, clienteAddress);
        if (cliente.senhaHash == senhaHash) {
            return (true, clienteAddress);
        } else {
            return (false, address(0));
        }
    }

    function login(string memory email, string memory senha) public returns (bool) {
        (bool autenticado, address clienteAddress) = autenticarCliente(email, senha);
        require(autenticado, "Credenciais invalidas!");
        require(clienteAddress == msg.sender, "Endereco de carteira nao corresponde!");
        emit clienteAutenticado(msg.sender, email, block.timestamp);
        return true;
    }

    function removerCliente(address cliente) public apenasDono {
        require(clientes[cliente].registrado, "Cliente nao existe");

        // Limpa os mappings de referência
        string memory referenciaPix = clientes[cliente].referenciaPix;
        string memory email = clientes[cliente].email;

        if (bytes(referenciaPix).length > 0) {
            delete pixCliente[referenciaPix];
        }

        if (bytes(email).length > 0) {
            delete emailCliente[email];
        }

        // Apaga o cliente
        delete clientes[cliente];
    }

    function alterarSenha(string memory senhaAtual, string memory novaSenha)
        public
        apenasClienteRegistrado
    {
        require(bytes(novaSenha).length >= 6, "Nova senha deve ter pelo menos 6 caracteres!");
        Cliente storage cliente = clientes[msg.sender];
        bytes32 senhaAtualHash = gerarHashSenha(senhaAtual, msg.sender);
        require(cliente.senhaHash == senhaAtualHash, "Senha atual incorreta!");
        cliente.senhaHash = gerarHashSenha(novaSenha, msg.sender);
    }

    // ========== Getters de apoio ==========
    function getEnderecoPorEmail(string memory email) public view returns (address) {
        return emailCliente[email];
    }

    function getEnderecoPorPix(string memory _referenciaPix) public view returns (address) {
        return pixCliente[_referenciaPix];
    }

    // ========== Info de cliente ==========
    function mostraInfoClienteEmail(string memory email)
        public
        view
        returns (address, string memory, uint256, bool, string memory)
    {
        address clienteAddress = emailCliente[email];
        require(clienteAddress != address(0), "Cliente nao encontrado para esse email");
        Cliente memory c = clientes[clienteAddress];
        // Retorna saldo ETH real da wallet em vez de saldo interno
        return (c.carteira, c.nome, c.carteira.balance, c.registrado, c.referenciaPix);
    }

    function mostraInfoCliente(string memory referenciaPix)
        public
        view
        returns (address, string memory, uint256, bool, string memory, string memory)
    {
        address clienteAddr = pixCliente[referenciaPix];
        require(clienteAddr != address(0), "Cliente nao encontrado para esse referenciaPix");

        Cliente memory c = clientes[clienteAddr];
        // Retorna saldo ETH real da wallet em vez de saldo interno
        return (c.carteira, c.nome, c.carteira.balance, c.registrado, c.referenciaPix, c.email);
    }

    function ClienteRegistrado(address cliente) public view returns (bool) {
        return clientes[cliente].registrado;
    }

    function getNomeCliente(address cliente) public view returns (string memory) {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        return clientes[cliente].nome;
    }

    function getEmailCliente(address cliente) public view returns (string memory) {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        return clientes[cliente].email;
    }

    function getReferenciaPixCliente(address cliente) public view returns (string memory) {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        return clientes[cliente].referenciaPix;
    }

    function getcarteiraPorEmail(string memory email) public view returns (address) {
        return emailCliente[email];
    }

    // Consulta saldo ETH real da wallet (não mais saldo interno)
    function saldoCliente(address cliente) external view returns (uint256) {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        return cliente.balance;
    }

    // Consulta saldo ETH real por referencia PIX
    function consultarSaldo(string memory _referenciaPix) public view returns (uint256) {
        address endereco = pixCliente[_referenciaPix];
        require(endereco != address(0), "Cliente nao encontrado");
        return endereco.balance;
    }

    // Transferencia ETH direta entre wallets (P2P puro)
    function transferirETHDireto(
        string memory _referenciaPix_destino,
        uint256 _valor
    ) public payable apenasClienteRegistrado {
        require(msg.value > 0, "Valor deve ser maior que zero");
        require(msg.value >= _valor, "ETH enviado insuficiente");

        address endereco_destino = pixCliente[_referenciaPix_destino];
        require(endereco_destino != address(0), "Cliente destino nao encontrado");
        require(endereco_destino != msg.sender, "Nao pode transferir para si mesmo");

        // Transferir ETH diretamente para a wallet de destino
        (bool success, ) = payable(endereco_destino).call{value: _valor}("");
        require(success, "Falha na transferencia de ETH");

        // Retornar troco se houver
        uint256 troco = msg.value - _valor;
        if (troco > 0) {
            (bool successTroco, ) = payable(msg.sender).call{value: troco}("");
            require(successTroco, "Falha ao retornar troco");
        }

        emit TransferenciaETH(msg.sender, endereco_destino, _valor);
    }

    // Função auxiliar para verificar se um endereço tem saldo suficiente
    function temSaldoSuficiente(address cliente, uint256 valor) external view returns (bool) {
        return cliente.balance >= valor;
    }

    // Transferir propriedade do contrato
    function transferirPropriedade(address novoDono) external apenasDono {
        require(novoDono != address(0), "Endereco invalido");
        dono = novoDono;
    }

    // Função para emergências - retirar ETH que possa ter ficado preso no contrato
    function sacarETHContrato(uint256 valor) external apenasDono {
        require(address(this).balance >= valor, "Saldo insuficiente no contrato");
        (bool success, ) = payable(dono).call{value: valor}("");
        require(success, "Falha ao sacar ETH do contrato");
    }

    // O contrato pode receber ETH
    receive() external payable {}
    fallback() external payable {}
}