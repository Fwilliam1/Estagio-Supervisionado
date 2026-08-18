import datetime
from django.test import TestCase
from models.usuario import Usuario
from services.usuario_service import UsuarioService
from services.jwt_service import JWTService
from services.exceptions import (
    NaoAutenticadoError,
    TokenInvalidoError,
    TokenExpiradoError,
    SessaoInvalidadaError,
)


class JWTServiceTestCase(TestCase):
    """Testes unitários para o JWTService."""

    def setUp(self):
        Usuario.objects.all().delete()
        self.usuario = UsuarioService.criar_usuario(
            nome="JWT User",
            email="jwt@teste.com",
            senha="senhaSegura123"
        )

    def test_gerar_e_validar_token_sucesso(self):
        token_info = JWTService.gerar_token(self.usuario)
        self.assertIn("token", token_info)
        self.assertEqual(token_info["tipo_token"], "Bearer")
        self.assertEqual(token_info["expira_em_segundos"], 7200)

        # Valida token gerado
        usuario_validado = JWTService.validar_token(token_info["token"])
        self.assertEqual(usuario_validado.id, self.usuario.id)
        self.assertEqual(usuario_validado.email, self.usuario.email)

    def test_validar_token_com_prefixo_bearer(self):
        token_info = JWTService.gerar_token(self.usuario)
        bearer_token = f"Bearer {token_info['token']}"
        usuario_validado = JWTService.validar_token(bearer_token)
        self.assertEqual(usuario_validado.id, self.usuario.id)

    def test_invalida_token_anterior_ao_gerar_novo_token(self):
        # 1. Primeiro login / geração de token
        token_1_info = JWTService.gerar_token(self.usuario)
        token_1 = token_1_info["token"]

        # O token 1 é válido inicialmente
        self.assertEqual(JWTService.validar_token(token_1).id, self.usuario.id)

        # 2. Segundo login / novo token gerado antes de expirar o primeiro
        token_2_info = JWTService.gerar_token(self.usuario)
        token_2 = token_2_info["token"]

        # O token 2 é válido
        self.assertEqual(JWTService.validar_token(token_2).id, self.usuario.id)

        # O token 1 DEVE ser invalidado
        with self.assertRaises(SessaoInvalidadaError):
            JWTService.validar_token(token_1)

    def test_validar_token_ausente(self):
        with self.assertRaises(NaoAutenticadoError):
            JWTService.validar_token(None)

        with self.assertRaises(NaoAutenticadoError):
            JWTService.validar_token("")

    def test_validar_token_invalido(self):
        with self.assertRaises(TokenInvalidoError):
            JWTService.validar_token("token.completamente.invalido")

    def test_invalidar_token_manualmente(self):
        token_info = JWTService.gerar_token(self.usuario)
        JWTService.invalidar_token(self.usuario)

        with self.assertRaises(SessaoInvalidadaError):
            JWTService.validar_token(token_info["token"])
