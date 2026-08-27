import io
from PIL import Image
from django.test import TestCase, Client
from models.usuario import Usuario
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.usuario_service import UsuarioService
from services.jwt_service import JWTService
from services.depth_service import DepthAnythingService
from services.dehazing_service import DehazingService


class DehazingDepthTestCase(TestCase):
    """Testes de integracao para Depth Anything V2 e UDPNet (FSNet OTS) Dehazing."""

    def setUp(self):
        self.client = Client()
        Usuario.objects.all().delete()
        Imagem.objects.all().delete()
        Algoritmo.objects.all().delete()

        self.usuario = UsuarioService.criar_usuario(
            nome="Tester Depth",
            email="depth_test@dsr.com",
            senha="senhaSegura123"
        )
        token_info = JWTService.gerar_token(self.usuario)
        self.token = token_info["token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        # Cria uma pequena imagem de teste 64x64
        self.img = Image.new('RGB', (64, 64), color=(120, 150, 180))
        buffer = io.BytesIO()
        self.img.save(buffer, format='PNG')
        self.img_bytes = buffer.getvalue()

    def test_servico_dehazing_pipeline_completo(self):
        resultado = DehazingService.processar_imagem(
            image_bytes=self.img_bytes,
            input_size=518
        )
        self.assertEqual(resultado["largura_original"], 64)
        self.assertEqual(resultado["altura_original"], 64)
        self.assertEqual(resultado["largura_processada"], 64)
        self.assertEqual(resultado["altura_processada"], 64)
        self.assertEqual(resultado["modelo_dehazing"], "UDPNet_FSNet_OTS")
        self.assertEqual(resultado["modelo_profundidade"], "DepthAnythingV2_ViTS")
        self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))
        self.assertTrue(resultado["mapa_profundidade_base64"].startswith("data:image/png;base64,"))
        self.assertGreater(len(resultado["imagem_processada_bytes"]), 0)

    def test_servico_depth_anything_vits_grayscale(self):
        resultado = DepthAnythingService.processar_imagem(
            image_bytes=self.img_bytes,
            encoder='vits',
            grayscale=True,
            input_size=518
        )
        self.assertEqual(resultado["largura_original"], 64)
        self.assertEqual(resultado["altura_original"], 64)
        self.assertEqual(resultado["largura_processada"], 64)
        self.assertEqual(resultado["altura_processada"], 64)
        self.assertEqual(resultado["encoder"], 'vits')
        self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))
        self.assertGreater(len(resultado["imagem_processada_bytes"]), 0)

    def test_servico_depth_anything_colormap(self):
        resultado = DepthAnythingService.processar_imagem(
            image_bytes=self.img_bytes,
            encoder='vits',
            grayscale=False,
            colormap='Spectral_r',
            input_size=518
        )
        self.assertEqual(resultado["largura_processada"], 64)
        self.assertEqual(resultado["altura_processada"], 64)
        self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))

    def test_endpoint_dehazing_sem_token_retorna_401(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "nevoa.png"
        response = self.client.post(
            '/api/processar/dehazing/',
            {'imagem': upload_file}
        )
        self.assertEqual(response.status_code, 401)

    def test_endpoint_dehazing_com_token_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "paisagem_nevoa.png"

        response = self.client.post(
            '/api/processar/dehazing/',
            {'imagem': upload_file},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["modelo_dehazing"], "UDPNet_FSNet_OTS")
        self.assertEqual(data["dados"]["modelo_profundidade"], "DepthAnythingV2_ViTS")
        self.assertEqual(data["dados"]["largura_processada"], 64)
        self.assertEqual(data["dados"]["altura_processada"], 64)

        # Verifica persistencia no banco
        self.assertEqual(Imagem.objects.filter(usuario=self.usuario).count(), 1)
        img_db = Imagem.objects.first()
        self.assertEqual(img_db.nomeArquivo, "paisagem_nevoa.png")
        self.assertIsNotNone(img_db.dadosProcessada)

    def test_endpoint_depth_com_token_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "depth_map.png"

        response = self.client.post(
            '/api/processar/depth/',
            {'imagem': upload_file},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["encoder"], 'vits')

