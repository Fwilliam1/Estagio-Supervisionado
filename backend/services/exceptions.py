class ServiceException(Exception):
    """Exceção base para erros na camada de serviço."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidacaoError(ServiceException):
    """Lançada quando os dados fornecidos são inválidos ou incompletos."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class UsuarioJaExisteError(ServiceException):
    """Lançada quando já existe um usuário com o mesmo e-mail."""
    def __init__(self, message: str = "Já existe um usuário cadastrado com este e-mail."):
        super().__init__(message, status_code=409)


class UsuarioNaoEncontradoError(ServiceException):
    """Lançada quando o usuário solicitado não for encontrado."""
    def __init__(self, message: str = "Usuário não encontrado."):
        super().__init__(message, status_code=404)


class CredenciaisInvalidasError(ServiceException):
    """Lançada quando e-mail ou senha forem inválidos durante a autenticação."""
    def __init__(self, message: str = "Credenciais inválidas. Verifique seu e-mail e senha."):
        super().__init__(message, status_code=401)


class NaoAutenticadoError(ServiceException):
    """Lançada quando a requisição não possui cabeçalho de autorização."""
    def __init__(self, message: str = "Acesso não autorizado. Token de autenticação não fornecido."):
        super().__init__(message, status_code=401)


class TokenInvalidoError(ServiceException):
    """Lançada quando o token JWT for inválido ou corrompido."""
    def __init__(self, message: str = "Token de autenticação inválido."):
        super().__init__(message, status_code=401)


class TokenExpiradoError(ServiceException):
    """Lançada quando o token JWT tiver expirado (validade de 2h)."""
    def __init__(self, message: str = "Token de autenticação expirado. Por favor, realize login novamente."):
        super().__init__(message, status_code=401)


class SessaoInvalidadaError(ServiceException):
    """Lançada quando um novo login foi realizado pelo mesmo usuário, invalidando o token anterior."""
    def __init__(self, message: str = "Sessão invalidada por um novo login. Por favor, realize login novamente."):
        super().__init__(message, status_code=401)

