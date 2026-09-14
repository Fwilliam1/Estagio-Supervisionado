import io
from PIL import Image
from django.test import TestCase, Client
from models.usuario import Usuario
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.usuario_service import UsuarioService
from services.jwt_service import JWTService
from services.convir_service import ConvIRService
from services.dehazing_service import DehazingService


class ConvIRTestCase(TestCase):
    """Testes de integração para o modelo ConvIR (small, pesos ots_small.pkl)."""

    def setUp(self):
        self.client = Client()
        Usuario.objects.all().delete()
        Imagem.objects.all().delete()
        Algoritmo.objects.all().delete()

        self.usuario = UsuarioService.criar_usuario(
            nome="Tester ConvIR",
            email="convir_test@dsr.com",
            senha="senhaSegura123"
        )
        token_info = JWTService.gerar_token(self.usuario)
        self.token = token_info["token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        # Imagem sintética de teste (64x64)
        self.img = Image.new('RGB', (64, 64), color=(140, 160, 190))
        buffer = io.BytesIO()
        self.img.save(buffer, format='PNG')
        self.img_bytes = buffer.getvalue()

    def test_convir_service_processar_imagem(self):
        resultado = ConvIRService.processar_imagem(
            image_bytes=self.img_bytes,
            version='small'
        )
        self.assertEqual(resultado["largura_original"], 64)
        self.assertEqual(resultado["altura_original"], 64)
        self.assertEqual(resultado["largura_processada"], 64)
        self.assertEqual(resultado["altura_processada"], 64)
        self.assertEqual(resultado["modelo_dehazing"], "ConvIR_small_OTS")
        self.assertEqual(resultado["pesos"], "ots_small.pkl")
        self.assertEqual(resultado["versao"], "small")
        self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))
        self.assertGreater(len(resultado["imagem_processada_bytes"]), 0)

    def test_dehazing_service_com_modelo_convir(self):
        resultado = DehazingService.processar_imagem(
            image_bytes=self.img_bytes,
            modelo='convir'
        )
        self.assertEqual(resultado["modelo_dehazing"], "ConvIR_small_OTS")
        self.assertEqual(resultado["largura_processada"], 64)
        self.assertEqual(resultado["altura_processada"], 64)

    def test_endpoint_convir_sem_token_retorna_401(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "haze_convir.png"
        response = self.client.post(
            '/api/processar/convir/',
            {'imagem': upload_file}
        )
        self.assertEqual(response.status_code, 401)

    def test_endpoint_convir_com_token_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "nevoa_convir.png"

        response = self.client.post(
            '/api/processar/convir/',
            {'imagem': upload_file},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["modelo_dehazing"], "ConvIR_small_OTS")
        self.assertEqual(data["dados"]["largura_processada"], 64)
        self.assertEqual(data["dados"]["altura_processada"], 64)

        # Verifica persistência no banco de dados
        self.assertEqual(Imagem.objects.filter(usuario=self.usuario).count(), 1)
        img_db = Imagem.objects.first()
        self.assertEqual(img_db.nomeArquivo, "nevoa_convir.png")
        self.assertIsNotNone(img_db.dadosProcessada)
        self.assertIn("ConvIR", img_db.algoritmo.tipo)

    def test_endpoint_dehazing_com_parametro_convir(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "nevoa_param_convir.png"

        response = self.client.post(
            '/api/processar/dehazing/',
            {'imagem': upload_file, 'modelo': 'convir'},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["modelo_dehazing"], "ConvIR_small_OTS")

    def test_endpoint_processar_router_com_algoritmo_convir(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "router_convir.png"

        response = self.client.post(
            '/api/processar/',
            {'imagem': upload_file, 'algoritmo': 'convir'},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["modelo_dehazing"], "ConvIR_small_OTS")
