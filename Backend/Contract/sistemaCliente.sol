pragma solidity ^0.8.19;

contract SistemaCliente {
    address public dono;

    struct Cliente {
        address carteira;
        string nome;
        uint256 saldo; // em Wei
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

    event TransferenciaSaldo(
        address indexed origem,
        address indexed destino,
        uint256 valor
    );

    event Saque(address indexed carteira, uint256 valor);

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
            saldo: 0,
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


    function getEndereco(string memory referenciaPix) public view returns (address) {
        return pixCliente[referenciaPix];
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
        return (c.carteira, c.nome, c.saldo, c.registrado, c.referenciaPix);
    }

    function mostraInfoCliente(address cliente)
        public
        view
        returns (address, string memory, uint256, bool, string memory, string memory)
    {
        Cliente memory c = clientes[cliente];
        return (c.carteira, c.nome, c.saldo, c.registrado, c.referenciaPix, c.email);
    }

    function mostraInfoClientePix(string memory referenciaPix)
        public
        view
        returns (address, string memory, uint256, bool, string memory)
    {
        address clienteAddress = pixCliente[referenciaPix];
        require(clienteAddress != address(0), "Cliente nao encontrado para essa referencia Pix");
        Cliente memory c = clientes[clienteAddress];
        // Corrigido: retorna a referenciaPix (nao o email)
        return (c.carteira, c.nome, c.saldo, c.registrado, c.referenciaPix);
    }

    function ClienteRegistrado(address cliente) public view returns (bool) {
        return clientes[cliente].registrado;
    }

    function getNomeCliente(address cliente) public view returns (string memory) {
        return clientes[cliente].nome;
    }

    function getEmailCliente(address cliente) public view returns (string memory) {
        return clientes[cliente].email;
    }

    function getReferenciaPixCliente(address cliente) public view returns (string memory) {
        return clientes[cliente].referenciaPix;
    }

    function getcarteiraPorEmail(string memory email) public view returns (address) {
        return emailCliente[email];
    }

    // ========== Saldos internos ==========
    // saldo do proprio cliente
    function saldoCliente() public view apenasClienteRegistrado returns (uint256) {
        return clientes[msg.sender].saldo;
    }

    // saldo de qualquer cliente (para UI)
    function saldoCliente(address cliente) external view returns (uint256) {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        return clientes[cliente].saldo;
    }

    // deposito de ETH para saldo interno
    function depositarSaldo() public payable apenasClienteRegistrado {
        require(msg.value > 0, "Valor precisa ser maior que zero");
        clientes[msg.sender].saldo += msg.value;
    }

    // saque de ETH do saldo interno
    function sacarSaldo(uint256 valorWei) public apenasClienteRegistrado {
        require(valorWei > 0, "Valor precisa ser maior que zero");
        require(clientes[msg.sender].saldo >= valorWei, "Saldo insuficiente");
        // effects
        clientes[msg.sender].saldo -= valorWei;
        // interaction
        (bool ok, ) = payable(msg.sender).call{value: valorWei}("");
        require(ok, "Falha ao enviar ETH");
        emit Saque(msg.sender, valorWei);
    }

    function sacarTudo() public apenasClienteRegistrado {
        uint256 valor = clientes[msg.sender].saldo;
        require(valor > 0, "Sem saldo a sacar");
        clientes[msg.sender].saldo = 0;
        (bool ok, ) = payable(msg.sender).call{value: valor}("");
        require(ok, "Falha ao enviar ETH");
        emit Saque(msg.sender, valor);
    }

    // transferencia de saldo interno entre clientes
    function transferirSaldo(
        string memory _referenciaPix_origem,
        string memory _referenciaPix_destino,
        uint256 _valor
    ) public {
        address endereco_origem = pixCliente[_referenciaPix_origem];
        address endereco_destino = pixCliente[_referenciaPix_destino];

        require(endereco_origem != address(0), "Cliente origem nao encontrado");
        require(endereco_destino != address(0), "Cliente destino nao encontrado");
        require(msg.sender == endereco_origem, "Apenas o proprietario pode transferir");
        require(clientes[endereco_origem].saldo >= _valor, "Saldo insuficiente");

        clientes[endereco_origem].saldo -= _valor;
        clientes[endereco_destino].saldo += _valor;

        emit TransferenciaSaldo(endereco_origem, endereco_destino, _valor);
    }

    // consulta saldo por referencia PIX
    function consultarSaldo(string memory _referenciaPix) public view returns (uint256) {
        address endereco = pixCliente[_referenciaPix];
        require(endereco != address(0), "Cliente nao encontrado");
        return clientes[endereco].saldo;
    }

    // ===== ajuste operacional protegido (use com cautela) =====
    function atualizarSaldoCliente(address cliente, uint256 novoSaldo) external apenasDono {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        clientes[cliente].saldo = novoSaldo;
    }

    // ===== Segurança extra: permitir atualizar dono se precisar =====
    function transferirPropriedade(address novoDono) external apenasDono {
        require(novoDono != address(0), "Endereco invalido");
        dono = novoDono;
    }

    // O contrato pode receber ETH (por segurança, nao credita automaticamente)
    receive() external payable {}
}
