import re
from typing import List, Dict, Any, Optional
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email as django_validate_email
from models.usuario import Usuario
from .exceptions import (
    ValidacaoError,
    UsuarioJaExisteError,
    UsuarioNaoEncontradoError,
)


class UsuarioService:
    """
    Camada de serviço responsável pelas regras de negócio e operações
    de persistência (CRUD) para a entidade Usuario.
    """

    @staticmethod
    def validar_email(email: str) -> str:
        """
        Valida e normaliza o formato do e-mail.
        """
        if not email or not isinstance(email, str) or not email.strip():
            raise ValidacaoError("O campo 'email' é obrigatório.")

        email_limpo = email.strip().lower()
        try:
            django_validate_email(email_limpo)
        except DjangoValidationError:
            raise ValidacaoError("O e-mail informado possui um formato inválido.")

        return email_limpo

    @staticmethod
    def validar_nome(nome: str) -> str:
        """
        Valida e normaliza o nome do usuário.
        """
        if not nome or not isinstance(nome, str) or not nome.strip():
            raise ValidacaoError("O campo 'nome' é obrigatório.")
        
        nome_limpo = nome.strip()
        if len(nome_limpo) < 2:
            raise ValidacaoError("O nome deve ter pelo menos 2 caracteres.")
        if len(nome_limpo) > 255:
            raise ValidacaoError("O nome não pode ter mais de 255 caracteres.")

        return nome_limpo

    @staticmethod
    def validar_senha(senha: str) -> str:
        """
        Valida os requisitos mínimos da senha.
        """
        if not senha or not isinstance(senha, str):
            raise ValidacaoError("O campo 'senha' é obrigatório.")
        if len(senha) < 6:
            raise ValidacaoError("A senha deve ter no mínimo 6 caracteres.")
        return senha

    @classmethod
    def criar_usuario(cls, nome: str, email: str, senha: str) -> Usuario:
        """
        Cria um novo usuário no banco de dados com senha criptografada em hash.
        """
        nome_valido = cls.validar_nome(nome)
        email_valido = cls.validar_email(email)
        senha_valida = cls.validar_senha(senha)

        # Verifica se o e-mail já está em uso
        if Usuario.objects.filter(email__iexact=email_valido).exists():
            raise UsuarioJaExisteError(f"O e-mail '{email_valido}' já está cadastrado.")

        usuario = Usuario(nome=nome_valido, email=email_valido)
        usuario.set_password(senha_valida)
        usuario.save()

        return usuario

    @classmethod
    def listar_usuarios(cls) -> List[Dict[str, Any]]:
        """
        Retorna a lista com todos os usuários cadastrados (sem expor senhas/hashes).
        """
        usuarios = Usuario.objects.all().order_by('id')
        return [cls.usuario_to_dict(u) for u in usuarios]

    @classmethod
    def obter_usuario_por_id(cls, usuario_id: int) -> Usuario:
        """
        Busca um usuário pelo ID. Lança UsuarioNaoEncontradoError se não existir.
        """
        if not usuario_id or not isinstance(usuario_id, int) or usuario_id <= 0:
            raise ValidacaoError("ID de usuário inválido.")

        usuario = Usuario.objects.filter(id=usuario_id).first()
        if not usuario:
            raise UsuarioNaoEncontradoError(f"Usuário com ID {usuario_id} não foi encontrado.")
        return usuario

    @classmethod
    def obter_usuario_por_email(cls, email: str) -> Usuario:
        """
        Busca um usuário pelo e-mail. Lança UsuarioNaoEncontradoError se não existir.
        """
        email_valido = cls.validar_email(email)
        usuario = Usuario.objects.filter(email__iexact=email_valido).first()
        if not usuario:
            raise UsuarioNaoEncontradoError(f"Usuário com e-mail '{email_valido}' não foi encontrado.")
        return usuario

    @classmethod
    def atualizar_usuario(
        cls,
        usuario_id: int,
        nome: Optional[str] = None,
        email: Optional[str] = None,
        senha: Optional[str] = None
    ) -> Usuario:
        """
        Atualiza dados de um usuário existente (nome, e-mail e/ou senha).
        """
        usuario = cls.obter_usuario_por_id(usuario_id)

        campos_alterados = False

        if nome is not None:
            nome_valido = cls.validar_nome(nome)
            usuario.nome = nome_valido
            campos_alterados = True

        if email is not None:
            email_valido = cls.validar_email(email)
            if email_valido != usuario.email.lower():
                if Usuario.objects.filter(email__iexact=email_valido).exclude(id=usuario.id).exists():
                    raise UsuarioJaExisteError(f"O e-mail '{email_valido}' já está sendo utilizado por outro usuário.")
                usuario.email = email_valido
                campos_alterados = True

        if senha is not None and senha != "":
            senha_valida = cls.validar_senha(senha)
            usuario.set_password(senha_valida)
            campos_alterados = True

        if campos_alterados:
            usuario.save()

        return usuario

    @classmethod
    def deletar_usuario(cls, usuario_id: int) -> bool:
        """
        Exclui um usuário do sistema pelo ID.
        """
        usuario = cls.obter_usuario_por_id(usuario_id)
        usuario.delete()
        return True

    @staticmethod
    def usuario_to_dict(usuario: Usuario) -> Dict[str, Any]:
        """
        Converte uma instância do modelo Usuario em dicionário seguro para serialização JSON.
        """
        return {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
        }
