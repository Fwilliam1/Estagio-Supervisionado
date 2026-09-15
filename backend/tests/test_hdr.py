import io
import json
from PIL import Image
from django.test import TestCase, Client
from models.usuario import Usuario
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.usuario_service import UsuarioService
from services.jwt_service import JWTService
from services.hdr_service import HDRService


class HDRTestCase(TestCase):
    """Testes de integracao para o servico SAFHDR e endpoints de processamento HDR."""

    def setUp(self):
        self.client = Client()
        Usuario.objects.all().delete()
        Imagem.objects.all().delete()
        Algoritmo.objects.all().delete()

        self.usuario = UsuarioService.criar_usuario(
            nome="Tester HDR",
            email="hdr_test@dsr.com",
            senha="senhaSegura123"
        )
        token_info = JWTService.gerar_token(self.usuario)
        self.token = token_info["token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        # Cria imagem de teste padrao 64x64
        self.img = Image.new('RGB', (64, 64), color=(140, 100, 80))
        buffer = io.BytesIO()
        self.img.save(buffer, format='PNG')
        self.img_bytes = buffer.getvalue()

    def test_servico_safhdr_dimensoes_padrao(self):
        resultado = HDRService.processar_imagem(self.img_bytes)
        self.assertEqual(resultado["largura_original"], 64)
        self.assertEqual(resultado["altura_original"], 64)
        self.assertEqual(resultado["largura_processada"], 64)
        self.assertEqual(resultado["altura_processada"], 64)
        self.assertEqual(resultado["modelo"], "SAFHDR")
        self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))
        self.assertGreater(len(resultado["imagem_processada_bytes"]), 0)
        self.assertIn("imagem_tonemapped", resultado)

    def test_servico_safhdr_dimensoes_impares_com_padding(self):
        # Testa resolucoes que causariam mismatch de tensores sem padding
        for width, height in [(65, 65), (71, 53), (100, 101)]:
            img_odd = Image.new('RGB', (width, height), color=(100, 120, 140))
            buf = io.BytesIO()
            img_odd.save(buf, format='PNG')
            resultado = HDRService.processar_imagem(buf.getvalue())
            self.assertEqual(resultado["largura_processada"], width)
            self.assertEqual(resultado["altura_processada"], height)
            self.assertTrue(resultado["imagem_processada_base64"].startswith("data:image/png;base64,"))

    def test_endpoint_hdr_sem_token_retorna_401(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "teste_hdr.png"
        response = self.client.post(
            '/api/processar/hdr/',
            {'imagem': upload_file, 'algoritmo': 'hdr'}
        )
        self.assertEqual(response.status_code, 401)

    def test_endpoint_hdr_com_token_multipart_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "teste_hdr_foto.png"

        response = self.client.post(
            '/api/processar/hdr/',
            {'imagem': upload_file, 'algoritmo': 'hdr'},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["modelo"], "SAFHDR")
        self.assertEqual(data["dados"]["largura_processada"], 64)
        self.assertEqual(data["dados"]["altura_processada"], 64)
        self.assertTrue(data["dados"]["imagem_base64"].startswith("data:image/"))

        # Verifica persistencia no banco de dados
        self.assertEqual(Imagem.objects.filter(usuario=self.usuario).count(), 1)
        img_db = Imagem.objects.first()
        self.assertEqual(img_db.nomeArquivo, "teste_hdr_foto.png")
        self.assertIn("SAFHDR", img_db.algoritmo.tipo)
        self.assertIsNotNone(img_db.dadosProcessada)

    def test_endpoint_processar_router_com_hdr_sucesso(self):
        upload_file = io.BytesIO(self.img_bytes)
        upload_file.name = "teste_router_hdr.png"

        response = self.client.post(
            '/api/processar/',
            {'imagem': upload_file, 'algoritmo': 'hdr'},
            **self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["dados"]["modelo"], "SAFHDR")
        self.assertTrue(data["dados"]["imagem_base64"].startswith("data:image/"))

    def test_salvar_imagem_historico_com_hdr(self):
        payload = {
            "email": "hdr_test@dsr.com",
            "inputImage": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            "processedImage": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            "process": "hdr",
            "fileName": "hdr_salvar_teste.png",
            "fileSize": "500 KB",
            "dimensions": "64x64"
        }

        response = self.client.post(
            '/api/imagens/salvar/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("db_id", data["item"])

        img_db = Imagem.objects.get(id=data["item"]["db_id"])
        self.assertIn("SAFHDR", img_db.algoritmo.tipo)
