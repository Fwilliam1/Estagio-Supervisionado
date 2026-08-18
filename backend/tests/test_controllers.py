import json
from django.test import TestCase, Client
from models.usuario import Usuario
from services.usuario_service import UsuarioService
from services.jwt_service import JWTService


class ControllersTestCase(TestCase):
    """Testes de integração para os controladores de Usuário e Autenticação com proteção JWT."""

    def setUp(self):
        self.client = Client()
        Usuario.objects.all().delete()
        self.usuario_base = UsuarioService.criar_usuario(
            nome="Admin DSR",
            email="admin@dsr.com",
            senha="adminPassword123"
        )
        # Gera token para o usuário base
        token_info = JWTService.gerar_token(self.usuario_base)
        self.token = token_info["token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    # ------------------ TESTES DE AUTENTICAÇÃO (LOGIN / CADASTRO) ------------------

    def test_endpoint_cadastrar_sucesso(self):
        payload = {
            "nome": "Novo Usuario",
            "email": "novocadastro@dsr.com",
            "senha": "senhaSegura123",
            "confirmacao_senha": "senhaSegura123"
        }
        response = self.client.post(
            '/api/auth/cadastrar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["email"], "novocadastro@dsr.com")
        self.assertEqual(data["dados"]["nome"], "Novo Usuario")
        self.assertNotIn("senha", data["dados"])
        self.assertNotIn("senha_hash", data["dados"])

    def test_endpoint_cadastrar_atalho_direto(self):
        payload = {
            "name": "Usuario Atalho",
            "email": "atalho@dsr.com",
            "password": "senhaSegura123",
            "confirmPassword": "senhaSegura123"
        }
        response = self.client.post(
            '/cadastrar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["email"], "atalho@dsr.com")

    def test_endpoint_cadastrar_email_duplicado(self):
        payload = {
            "nome": "Duplicado",
            "email": "admin@dsr.com",
            "senha": "senhaSegura123"
        }
        response = self.client.post(
            '/api/auth/cadastrar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data["status"], "erro")

    def test_endpoint_login_sucesso_retorna_jwt(self):
        payload = {
            "email": "admin@dsr.com",
            "senha": "adminPassword123"
        }
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertIn("token", data)
        self.assertEqual(data["tipo_token"], "Bearer")
        self.assertEqual(data["expira_em_segundos"], 7200)
        self.assertEqual(data["dados"]["id"], self.usuario_base.id)
        self.assertEqual(data["dados"]["email"], "admin@dsr.com")

    def test_endpoint_login_invalida_token_anterior_em_novo_login(self):
        # 1. Login inicial
        resp1 = self.client.post(
            '/api/login/',
            data=json.dumps({"email": "admin@dsr.com", "senha": "adminPassword123"}),
            content_type='application/json'
        )
        token_1 = resp1.json()["token"]

        # O token 1 funciona
        resp_me1 = self.client.get('/api/me/', HTTP_AUTHORIZATION=f"Bearer {token_1}")
        self.assertEqual(resp_me1.status_code, 200)

        # 2. Novo login realizado pelo mesmo usuário antes de 2h
        resp2 = self.client.post(
            '/api/login/',
            data=json.dumps({"email": "admin@dsr.com", "senha": "adminPassword123"}),
            content_type='application/json'
        )
        token_2 = resp2.json()["token"]

        # O token 2 funciona
        resp_me2 = self.client.get('/api/me/', HTTP_AUTHORIZATION=f"Bearer {token_2}")
        self.assertEqual(resp_me2.status_code, 200)

        # O token 1 agora está INVALIDADO
        resp_me1_novo = self.client.get('/api/me/', HTTP_AUTHORIZATION=f"Bearer {token_1}")
        self.assertEqual(resp_me1_novo.status_code, 401)
        self.assertIn("Sessão invalidada por um novo login", resp_me1_novo.json()["mensagem"])

    def test_endpoint_login_senha_incorreta(self):
        payload = {
            "email": "admin@dsr.com",
            "senha": "senhaTotalmenteIncorreta"
        }
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "erro")

    def test_endpoint_me_com_token_valido(self):
        response = self.client.get('/api/auth/me/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["dados"]["email"], "admin@dsr.com")

    def test_endpoint_me_sem_token_retorna_401(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)

    def test_endpoint_logout_invalida_token(self):
        # Chama logout com o token
        response = self.client.post('/api/auth/logout/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)

        # Tentativa de usar o token após logout deve falhar
        response_me = self.client.get('/api/auth/me/', **self.auth_headers)
        self.assertEqual(response_me.status_code, 401)

    # ------------------ TESTES DO CRUD DE USUÁRIOS (PROTEGIDO POR JWT) ------------------

    def test_listar_usuarios_sem_token_retorna_401(self):
        response = self.client.get('/api/usuarios/')
        self.assertEqual(response.status_code, 401)

    def test_listar_usuarios_com_token_valido(self):
        response = self.client.get('/api/usuarios/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["quantidade"], 1)
        self.assertEqual(data["dados"][0]["email"], "admin@dsr.com")

    def test_criar_usuario_via_crud_com_token(self):
        payload = {
            "nome": "Segundo Usuario",
            "email": "segundo@dsr.com",
            "senha": "senhaSegura123"
        }
        response = self.client.post(
            '/api/usuarios/',
            data=json.dumps(payload),
            content_type='application/json',
            **self.auth_headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["email"], "segundo@dsr.com")

    def test_obter_usuario_por_id_endpoint(self):
        response = self.client.get(f'/api/usuarios/{self.usuario_base.id}/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["id"], self.usuario_base.id)

    def test_obter_usuario_por_id_inexistente_endpoint(self):
        response = self.client.get('/api/usuarios/99999/', **self.auth_headers)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["status"], "erro")

    def test_atualizar_usuario_endpoint(self):
        payload = {
            "nome": "Admin Nome Alterado",
            "email": "admin_novo@dsr.com"
        }
        response = self.client.put(
            f'/api/usuarios/{self.usuario_base.id}/',
            data=json.dumps(payload),
            content_type='application/json',
            **self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["dados"]["nome"], "Admin Nome Alterado")
        self.assertEqual(data["dados"]["email"], "admin_novo@dsr.com")

    def test_deletar_usuario_endpoint(self):
        novo = UsuarioService.criar_usuario("Deletar", "del@dsr.com", "senha123")
        response = self.client.delete(f'/api/usuarios/{novo.id}/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Usuario.objects.filter(id=novo.id).count(), 0)
