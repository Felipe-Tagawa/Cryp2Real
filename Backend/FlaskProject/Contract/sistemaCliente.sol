pragma solidity ^0.8.19;

contract SistemaCliente {

    struct Cliente {
        address carteira;
        string nome;
        uint256 saldo; // Wei
        bool registrado;
        string referenciaPix;
        string email;
        bytes32 senhaHash;
    }

    mapping(address => Cliente) public clientes;
    mapping(string => address) public pixCliente;
    mapping(string => address) public emailCliente;
    mapping(string => address) private pixParaEndereco;

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

    function gerarHashSenha(string memory senha, address salt)
        private
        pure
        returns (bytes32)
    {
        return keccak256(abi.encodePacked(senha, salt));
    }

    function registrarCliente(
        string memory nome,
        string memory _referenciaPix,
        string memory email,
        string memory senha) public {
        require(!clientes[msg.sender].registrado, "Cliente ja registrado!");
        require(bytes(_referenciaPix).length > 0, "Referencia PIX invalida!");
        require(bytes(email).length > 0, "Email invalido!");
        require(bytes(senha).length >= 6, "Senha deve ter pelo menos 6 caracteres!");
        // require(pixCliente[_referenciaPix] == address(0), "Referencia Pix ja utilizada anteriormente!");
        // require(emailCliente[email] == address(0), "Email ja utilizado anteriormente!");

        bytes32 senhaHash = gerarHashSenha(senha, msg.sender);

        clientes[msg.sender] = Cliente({
            carteira: msg.sender,
            nome: nome,
            saldo: 10,
            registrado: true,
            referenciaPix: _referenciaPix,
            email: email,
            senhaHash: senhaHash
        });

        pixCliente[_referenciaPix] = msg.sender;
        pixParaEndereco[_referenciaPix] = msg.sender;
        emailCliente[email] = msg.sender;

        emit novoClienteRegistrado(msg.sender, nome, _referenciaPix, email);
    }

    function getEnderecoPorEmail(string memory email) public view returns (address) {
    return emailCliente[email];
    }

    function getEnderecoPorPix(string memory _referenciaPix) public view returns (address) {
        return pixParaEndereco[_referenciaPix];
    }

    // Apenas para testar:
    function adicionarSaldo(string memory referenciaPix, uint valor) public {
        address cliente = pixParaEndereco[referenciaPix];
        require(clientes[cliente].registrado, "Cliente nao registrado");
        clientes[cliente].saldo += valor;
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

    function login(string memory email, string memory senha)
        public
        returns (bool)
    {
        (bool autenticado, address clienteAddress) = autenticarCliente(email, senha);
        require(autenticado, "Credenciais invalidas!");
        require(clienteAddress == msg.sender, "Endereco de carteira nao corresponde!");

        emit clienteAutenticado(msg.sender, email, block.timestamp);
        return true;
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
        return (c.carteira, c.nome, c.saldo, c.registrado, c.email);
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

    modifier apenasClienteRegistrado() {
        require(clientes[msg.sender].registrado, "Cliente nao registrado!");
        _;
    }

    function saldoCliente(address cliente) public view apenasClienteRegistrado returns (uint256) {
        return clientes[msg.sender].saldo;
    }

    // IMPORTANTE: Função para permitir que outros contratos atualizem o saldo
    function atualizarSaldoCliente(address cliente, uint256 novoSaldo) external {
        require(clientes[cliente].registrado, "Cliente nao registrado!");
        clientes[cliente].saldo = novoSaldo;
    }

    function depositarSaldo() public payable apenasClienteRegistrado {
        require(msg.value > 0, "Valor precisa ser maior que zero");
        clientes[msg.sender].saldo += msg.value;
    }
        // Função para transferir saldo entre clientes
    function transferirSaldo(
        string memory _referenciaPix_origem,
        string memory _referenciaPix_destino,
        uint256 _valor
    ) public {
        address endereco_origem = pixParaEndereco[_referenciaPix_origem];
        address endereco_destino = pixParaEndereco[_referenciaPix_destino];

        require(endereco_origem != address(0), "Cliente origem nao encontrado");
        require(endereco_destino != address(0), "Cliente destino nao encontrado");
        require(msg.sender == endereco_origem, "Apenas o proprietario pode transferir");
        require(saldos[endereco_origem] >= _valor, "Saldo insuficiente");

        // Realizar transferência
        saldos[endereco_origem] -= _valor;
        saldos[endereco_destino] += _valor;

        emit TransferenciaSaldo(endereco_origem, endereco_destino, _valor);
    }

    // Função para consultar saldo por referência PIX
    function consultarSaldo(string memory _referenciaPix) public view returns (uint256) {
        address endereco = pixParaEndereco[_referenciaPix];
        require(endereco != address(0), "Cliente nao encontrado");
        return saldos[endereco];
    }

    // Função para obter endereço por PIX
    function getEnderecoPorPix(string memory _referenciaPix) public view returns (address) {
        return pixParaEndereco[_referenciaPix];
    }

    // Event para transferências
    event TransferenciaSaldo(
        address indexed origem,
        address indexed destino,
        uint256 valor
    );

}
