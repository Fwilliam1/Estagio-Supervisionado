from django.test import TestCase
from models.usuario import Usuario
from services.usuario_service import UsuarioService
from services.auth_service import AuthService
from services.exceptions import (
    ValidacaoError,
    UsuarioJaExisteError,
    CredenciaisInvalidasError,
)


class AuthServiceTestCase(TestCase):
    """Testes unitários para AuthService."""

    def setUp(self):
        Usuario.objects.all().delete()
        self.usuario_base = UsuarioService.criar_usuario(
            nome="Usuario Teste",
            email="auth@teste.com",
            senha="senhaPadrao123"
        )

    def test_cadastrar_sucesso(self):
        resultado = AuthService.cadastrar(
            nome="Novo Usuario",
            email="novo@teste.com",
            senha="senhaNova123",
            confirmacao_senha="senhaNova123"
        )
        self.assertIn("mensagem", resultado)
        self.assertIn("usuario", resultado)
        self.assertEqual(resultado["usuario"]["nome"], "Novo Usuario")
        self.assertEqual(resultado["usuario"]["email"], "novo@teste.com")

    def test_cadastrar_senhas_diferentes(self):
        with self.assertRaises(ValidacaoError):
            AuthService.cadastrar(
                nome="Usuario Mismatch",
                email="mismatch@teste.com",
                senha="senhaValida123",
                confirmacao_senha="outraSenhaIncorreta"
            )

    def test_autenticar_sucesso(self):
        resultado = AuthService.autenticar(
            email="auth@teste.com",
            senha="senhaPadrao123"
        )
        self.assertIn("token", resultado)
        self.assertEqual(resultado["tipo_token"], "Bearer")
        self.assertEqual(resultado["expira_em_segundos"], 7200)
        self.assertEqual(resultado["usuario"].id, self.usuario_base.id)
        self.assertEqual(resultado["usuario"].email, "auth@teste.com")


    def test_autenticar_senha_incorreta(self):
        with self.assertRaises(CredenciaisInvalidasError):
            AuthService.autenticar(
                email="auth@teste.com",
                senha="senhaErrada"
            )

    def test_autenticar_email_inexistente(self):
        with self.assertRaises(CredenciaisInvalidasError):
            AuthService.autenticar(
                email="naoexiste@teste.com",
                senha="senhaPadrao123"
            )

    def test_autenticar_campos_vazios(self):
        with self.assertRaises(ValidacaoError):
            AuthService.autenticar(email="", senha="123")

        with self.assertRaises(ValidacaoError):
            AuthService.autenticar(email="auth@teste.com", senha="")
