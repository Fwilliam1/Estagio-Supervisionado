from typing import Dict, Any, Optional
from models.usuario import Usuario
from .usuario_service import UsuarioService
from .jwt_service import JWTService
from .exceptions import (
    ValidacaoError,
    CredenciaisInvalidasError,
)


class AuthService:
    """
    Camada de serviço responsável pelos fluxos de autenticação (Login e Cadastro).
    """

    @classmethod
    def cadastrar(
        cls,
        nome: str,
        email: str,
        senha: str,
        confirmacao_senha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Realiza o cadastro de um novo usuário, com validação de confirmação de senha opcional.
        """
        if confirmacao_senha is not None and senha != confirmacao_senha:
            raise ValidacaoError("As senhas informadas não coincidem.")

        usuario = UsuarioService.criar_usuario(nome=nome, email=email, senha=senha)

        return {
            "mensagem": "Cadastro realizado com sucesso.",
            "usuario": UsuarioService.usuario_to_dict(usuario)
        }

    @classmethod
    def autenticar(cls, email: str, senha: str) -> Dict[str, Any]:
        """
        Autentica o usuário validando e-mail e senha com hash.
        Gera um token JWT com validade de 2 horas e invalida qualquer sessão anterior.
        Lança CredenciaisInvalidasError se os dados não baterem.
        """
        if not email or not isinstance(email, str) or not email.strip():
            raise ValidacaoError("O e-mail é obrigatório para realizar login.")

        if not senha or not isinstance(senha, str):
            raise ValidacaoError("A senha é obrigatória para realizar login.")

        email_limpo = email.strip().lower()
        usuario = Usuario.objects.filter(email__iexact=email_limpo).first()

        if not usuario or not usuario.check_password(senha):
            raise CredenciaisInvalidasError("E-mail ou senha incorretos.")

        # Gera o token JWT de 2h e atualiza a versão da sessão do usuário
        token_info = JWTService.gerar_token(usuario)

        return {
            "usuario": usuario,
            "token": token_info["token"],
            "tipo_token": token_info["tipo_token"],
            "expira_em_segundos": token_info["expira_em_segundos"],
            "expira_em": token_info["expira_em"]
        }

    @classmethod
    def logout(cls, usuario: Usuario) -> None:
        """
        Realiza logout invalidando o token do usuário.
        """
        JWTService.invalidar_token(usuario)

