from django.test import TestCase
from models.usuario import Usuario
from services.usuario_service import UsuarioService
from services.exceptions import (
    ValidacaoError,
    UsuarioJaExisteError,
    UsuarioNaoEncontradoError,
)


class UsuarioServiceTestCase(TestCase):
    """Testes unitários para UsuarioService."""

    def setUp(self):
        Usuario.objects.all().delete()
        self.usuario_base = UsuarioService.criar_usuario(
            nome="Maria Silva",
            email="maria@teste.com",
            senha="senhaSegura123"
        )

    def test_criar_usuario_sucesso(self):
        usuario = UsuarioService.criar_usuario(
            nome="João Santos",
            email="joao@teste.com",
            senha="outraSenha123"
        )
        self.assertIsNotNone(usuario.id)
        self.assertEqual(usuario.nome, "João Santos")
        self.assertEqual(usuario.email, "joao@teste.com")
        self.assertTrue(usuario.check_password("outraSenha123"))
        self.assertFalse(usuario.check_password("senhaErrada"))
        self.assertNotEqual(usuario.senha_hash, "outraSenha123")

    def test_criar_usuario_email_duplicado(self):
        with self.assertRaises(UsuarioJaExisteError):
            UsuarioService.criar_usuario(
                nome="Outra Maria",
                email="MARIA@teste.com",  # teste case-insensitivity
                senha="senhaValida123"
            )

    def test_criar_usuario_email_invalido(self):
        with self.assertRaises(ValidacaoError):
            UsuarioService.criar_usuario(
                nome="Teste Email",
                email="email-invalido",
                senha="senhaValida123"
            )

    def test_criar_usuario_senha_curta(self):
        with self.assertRaises(ValidacaoError):
            UsuarioService.criar_usuario(
                nome="Teste Senha",
                email="teste_curta@teste.com",
                senha="123"
            )

    def test_criar_usuario_nome_vazio(self):
        with self.assertRaises(ValidacaoError):
            UsuarioService.criar_usuario(
                nome="   ",
                email="teste_nome@teste.com",
                senha="senhaValida123"
            )

    def test_listar_usuarios(self):
        UsuarioService.criar_usuario(
            nome="Carlos Oliveira",
            email="carlos@teste.com",
            senha="senhaValida123"
        )
        lista = UsuarioService.listar_usuarios()
        self.assertEqual(len(lista), 2)
        self.assertEqual(lista[0]["email"], "maria@teste.com")
        self.assertEqual(lista[1]["email"], "carlos@teste.com")
        self.assertNotIn("senha_hash", lista[0])

    def test_obter_usuario_por_id_sucesso(self):
        usuario = UsuarioService.obter_usuario_por_id(self.usuario_base.id)
        self.assertEqual(usuario.id, self.usuario_base.id)
        self.assertEqual(usuario.email, "maria@teste.com")

    def test_obter_usuario_por_id_inexistente(self):
        with self.assertRaises(UsuarioNaoEncontradoError):
            UsuarioService.obter_usuario_por_id(99999)

    def test_obter_usuario_por_email_sucesso(self):
        usuario = UsuarioService.obter_usuario_por_email("maria@teste.com")
        self.assertEqual(usuario.id, self.usuario_base.id)

    def test_obter_usuario_por_email_inexistente(self):
        with self.assertRaises(UsuarioNaoEncontradoError):
            UsuarioService.obter_usuario_por_email("inexistente@teste.com")

    def test_atualizar_usuario_sucesso(self):
        usuario_atualizado = UsuarioService.atualizar_usuario(
            usuario_id=self.usuario_base.id,
            nome="Maria Silva Atualizada",
            email="maria.nova@teste.com",
            senha="novaSenhaForte123"
        )
        self.assertEqual(usuario_atualizado.nome, "Maria Silva Atualizada")
        self.assertEqual(usuario_atualizado.email, "maria.nova@teste.com")
        self.assertTrue(usuario_atualizado.check_password("novaSenhaForte123"))

    def test_atualizar_usuario_email_duplicado(self):
        UsuarioService.criar_usuario(
            nome="Outro",
            email="outro@teste.com",
            senha="senhaValida123"
        )
        with self.assertRaises(UsuarioJaExisteError):
            UsuarioService.atualizar_usuario(
                usuario_id=self.usuario_base.id,
                email="outro@teste.com"
            )

    def test_deletar_usuario_sucesso(self):
        resultado = UsuarioService.deletar_usuario(self.usuario_base.id)
        self.assertTrue(resultado)
        self.assertEqual(Usuario.objects.filter(id=self.usuario_base.id).count(), 0)

    def test_deletar_usuario_inexistente(self):
        with self.assertRaises(UsuarioNaoEncontradoError):
            UsuarioService.deletar_usuario(99999)
