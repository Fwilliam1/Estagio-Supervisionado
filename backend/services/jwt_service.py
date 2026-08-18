import uuid
import datetime
from typing import Dict, Any, Optional
import jwt
from django.conf import settings
from models.usuario import Usuario
from .exceptions import (
    NaoAutenticadoError,
    TokenInvalidoError,
    TokenExpiradoError,
    SessaoInvalidadaError,
)


class JWTService:
    """
    Serviço para geração, validação e invalidação de JSON Web Tokens (JWT).
    Garante validade de 2 horas e sessão única por usuário (invalidação em caso de novo login).
    """
    DURACAO_TOKEN_HORAS = 2
    DURACAO_TOKEN_SEGUNDOS = DURACAO_TOKEN_HORAS * 3600  # 7200 segundos
    ALGORITMO = 'HS256'

    @classmethod
    def gerar_token(cls, usuario: Usuario) -> Dict[str, Any]:
        """
        Gera um novo token JWT com validade de 2 horas.
        Gera uma nova 'token_versao' no registro do usuário, o que invalida
        automaticamente qualquer token anterior que estivesse ativo.
        """
        # Cria novo identificador de versão de sessão
        nova_versao = uuid.uuid4().hex
        usuario.token_versao = nova_versao
        usuario.save(update_fields=['token_versao'])

        agora = datetime.datetime.now(datetime.timezone.utc)
        expiracao = agora + datetime.timedelta(hours=cls.DURACAO_TOKEN_HORAS)

        payload = {
            "sub": str(usuario.id),
            "usuario_id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "token_versao": nova_versao,
            "iat": int(agora.timestamp()),
            "exp": int(expiracao.timestamp()),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=cls.ALGORITMO)

        return {
            "token": token,
            "tipo_token": "Bearer",
            "expira_em_segundos": cls.DURACAO_TOKEN_SEGUNDOS,
            "expira_em": expiracao.isoformat()
        }

    @classmethod
    def validar_token(cls, token_raw: Optional[str]) -> Usuario:
        """
        Valida a assinatura, expiração e integridade do token JWT.
        Verifica se a versão do token coincide com a versão atual do usuário no banco.
        Se outro login tiver ocorrido, lança SessaoInvalidadaError.
        """
        if not token_raw or not isinstance(token_raw, str) or not token_raw.strip():
            raise NaoAutenticadoError("Token de autenticação não fornecido.")

        token = token_raw.strip()
        if token.lower().startswith('bearer '):
            token = token[7:].strip()

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[cls.ALGORITMO]
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiradoError("Token de autenticação expirado (validade de 2 horas excedida). Por favor, realize login novamente.")
        except jwt.InvalidTokenError:
            raise TokenInvalidoError("Token de autenticação inválido ou corrompido.")

        usuario_id = payload.get('usuario_id')
        token_versao = payload.get('token_versao')

        if not usuario_id or not token_versao:
            raise TokenInvalidoError("Estrutura do token inválida.")

        usuario = Usuario.objects.filter(id=usuario_id).first()
        if not usuario:
            raise TokenInvalidoError("Usuário associado ao token não foi encontrado.")

        # Verifica se o token pertence à sessão ativa mais recente
        if usuario.token_versao != token_versao:
            raise SessaoInvalidadaError("Sessão invalidada por um novo login. Por favor, autentique-se novamente.")

        return usuario

    @classmethod
    def invalidar_token(cls, usuario: Usuario) -> None:
        """
        Invalida a sessão/token atual do usuário alterando sua 'token_versao'.
        """
        usuario.token_versao = uuid.uuid4().hex
        usuario.save(update_fields=['token_versao'])
