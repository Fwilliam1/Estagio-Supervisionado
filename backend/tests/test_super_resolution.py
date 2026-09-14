import io
from PIL import Image
from django.test import TestCase, Client
from models.usuario import Usuario
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.usuario_service import UsuarioService
from services.jwt_service import JWTService
from services.super_resolution_service import SuperResolutionService


class SuperResolutionTestCase(TestCase):
    """Testes de integração para Super-Resolução ESC e endpoints de processamento."""

    def setUp(self):
        self.client = Client()
        Usuario.objects.all().delete()
        Imagem.objects.all().delete()
        Algoritmo.objects.all().delete()

        self.usuario = UsuarioService.criar_usuario(
            nome="Tester SR",
            email="sr_test@dsr.com",
            senha="senhaSegura123"
        )
        token_info = JWTService.gerar_token(self.usuario)
        self.token = token_info["token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        # Cria uma pequena imagem de teste 64x64
        self.img = Image.new('RGB', (64, 64), color=(73, 109, 137))
        buffer = io.BytesIO()
        self.img.save(buffer, format='PNG')
        self.img_bytes = buffer.getvalue()

    def test_servico_dmnet_x2_x3_x4(self):
        for scale in (2, 3, 4):
            resultado = SuperResolutionService.processar_imagem(self.img_bytes, scale=scale, model_name='DMNet')
            self.assertEqual(resultado["largura_original"], 64)
            self.assertEqual(resultado["altura_original"], 64)
            self.assertEqual(resultado["largura_processada"], 64 * scale)
            self.assertEqual(resultado["altura_processada"], 64 * scale)
            self.assertEqual(resultado["escala"], scale)
            self.assertEqual(resultado["modelo"], "DMNet")
            self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))
            self.assertGreater(len(resultado["imagem_processada_bytes"]), 0)

    def test_servico_esc_x2_x3_x4(self):
        for scale in (2, 3, 4):
            resultado = SuperResolutionService.processar_imagem(self.img_bytes, scale=scale, model_name='ESC')
            self.assertEqual(resultado["largura_original"], 64)
            self.assertEqual(resultado["altura_original"], 64)
            self.assertEqual(resultado["largura_processada"], 64 * scale)
            self.assertEqual(resultado["altura_processada"], 64 * scale)
            self.assertEqual(resultado["escala"], scale)
            self.assertEqual(resultado["modelo"], "ESC")
            self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))
            self.assertGreater(len(resultado["imagem_processada_bytes"]), 0)

    def test_endpoint_super_resolucao_sem_token_retorna_401(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "teste.png"
        response = self.client.post(
            '/api/processar/super-resolution/',
            {'imagem': upload_file, 'scale': 2}
        )
        self.assertEqual(response.status_code, 401)

    def test_endpoint_super_resolucao_com_token_dmnet_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "teste_dmnet.png"

        response = self.client.post(
            '/api/processar/super-resolution/',
            {'imagem': upload_file, 'scale': 2, 'model': 'DMNet'},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["escala"], 2)
        self.assertEqual(data["dados"]["modelo"], "DMNet")
        self.assertEqual(data["dados"]["largura_processada"], 128)
        self.assertEqual(data["dados"]["altura_processada"], 128)

        # Verifica se gravou no banco de dados
        self.assertEqual(Imagem.objects.filter(usuario=self.usuario).count(), 1)
        img_db = Imagem.objects.first()
        self.assertEqual(img_db.nomeArquivo, "teste_dmnet.png")
        self.assertEqual(img_db.resolucao, "128x128")
        self.assertIn("DMNet", img_db.algoritmo.tipo)
        self.assertIsNotNone(img_db.dadosProcessada)

    def test_endpoint_super_resolucao_com_token_esc_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "teste_esc.png"

        response = self.client.post(
            '/api/processar/super-resolution/',
            {'imagem': upload_file, 'scale': 3, 'model': 'ESC'},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["escala"], 3)
        self.assertEqual(data["dados"]["modelo"], "ESC")
        self.assertEqual(data["dados"]["largura_processada"], 192)
        self.assertEqual(data["dados"]["altura_processada"], 192)
