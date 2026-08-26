import json
import base64
from typing import Dict, Any, Tuple
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.super_resolution_service import SuperResolutionService
from services.exceptions import ServiceException, ValidacaoError
from .decorators import requer_autenticacao


def _extrair_imagem_e_parametros(request: HttpRequest) -> Tuple[bytes, str, int, str]:
    """
    Extrai bytes da imagem, nome do arquivo, escala e tipo de algoritmo
    a partir de multipart/form-data ou JSON.
    """
    nome_arquivo = "imagem_upload.png"
    escala = 2
    tipo_algoritmo = "super-resolution"
    image_bytes = b""

    # 1. Se enviado via Multipart Form Data (Upload de arquivo)
    if request.FILES:
        arquivo = (
            request.FILES.get('imagem') or
            request.FILES.get('image') or
            request.FILES.get('file')
        )
        if arquivo:
            image_bytes = arquivo.read()
            nome_arquivo = arquivo.name

        escala = request.POST.get('scale') or request.POST.get('escala') or 2
        tipo_algoritmo = request.POST.get('algoritmo') or request.POST.get('algorithm') or "super-resolution"

    # 2. Se enviado via JSON Body (Base64)
    elif request.body:
        try:
            body = json.loads(request.body.decode('utf-8'))
            if isinstance(body, dict):
                b64_data = (
                    body.get('imagem_base64') or
                    body.get('image_base64') or
                    body.get('imagem') or
                    body.get('image') or
                    body.get('dadosOriginal')
                )
                if b64_data:
                    # Remove cabeçalho data:image/...;base64, se existir
                    if ',' in b64_data:
                        b64_data = b64_data.split(',', 1)[1]
                    image_bytes = base64.b64decode(b64_data)

                nome_arquivo = body.get('nome_arquivo') or body.get('filename') or nome_arquivo
                escala = body.get('scale') or body.get('escala') or 2
                tipo_algoritmo = body.get('algoritmo') or body.get('algorithm') or "super-resolution"
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            raise ValidacaoError(f"Erro ao processar dados JSON da requisição: {str(e)}")

    if not image_bytes:
        raise ValidacaoError("Nenhum arquivo ou dado de imagem foi enviado na requisição.")

    try:
        escala_int = int(escala)
    except (ValueError, TypeError):
        escala_int = 2

    return image_bytes, nome_arquivo, escala_int, tipo_algoritmo


@csrf_exempt
@requer_autenticacao
def super_resolution_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para aplicar Super-Resolução com a arquitetura ESC (x2, x3, x4).
    POST /api/processar/super-resolution/ ou POST /api/processar/
    Requer token JWT no cabeçalho Authorization: Bearer <token>
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        # 1. Extração dos dados da requisição
        image_bytes, nome_arquivo, escala, tipo_algoritmo = _extrair_imagem_e_parametros(request)

        # 2. Execução da inferência da rede neural ESC
        resultado = SuperResolutionService.processar_imagem(
            image_bytes=image_bytes,
            scale=escala
        )

        # 3. Registro do algoritmo e imagem no banco de dados
        usuario = request.usuario

        algoritmo_instancia, _ = Algoritmo.objects.get_or_create(
            tipo=f"ESC_SuperResolution_X{escala}",
            defaults={
                "parametros": json.dumps({
                    "modelo": "ESC",
                    "dataset_treino": "DIV2K",
                    "escala": escala,
                    "pesos": f"ESC_DIV2K_X{escala}.pth",
                    "attn_type": "SDPA"
                })
            }
        )

        # Determina extensão/formato
        formato = "PNG"
        if "." in nome_arquivo:
            formato = nome_arquivo.rsplit(".", 1)[-1].upper()

        registro_imagem = Imagem.objects.create(
            usuario=usuario,
            algoritmo=algoritmo_instancia,
            nomeArquivo=nome_arquivo,
            formato=formato,
            resolucao=resultado["resolucao_processada"],
            tamanho=resultado["tamanho_processado_kb"],
            dadosOriginal=image_bytes,
            dadosProcessada=resultado["imagem_processada_bytes"]
        )

        return JsonResponse({
            "status": "sucesso",
            "mensagem": f"Super-resolução {escala}x aplicada com sucesso via rede ESC!",
            "dados": {
                "imagem_id": registro_imagem.id,
                "nome_arquivo": nome_arquivo,
                "imagem_base64": resultado["imagem_processada_base64"],
                "resolucao_original": resultado["resolucao_original"],
                "resolucao_processada": resultado["resolucao_processada"],
                "largura_original": resultado["largura_original"],
                "altura_original": resultado["altura_original"],
                "largura_processada": resultado["largura_processada"],
                "altura_processada": resultado["altura_processada"],
                "escala": resultado["escala"],
                "tempo_execucao_segundos": resultado["tempo_execucao_segundos"],
                "tamanho_original_kb": resultado["tamanho_original_kb"],
                "tamanho_processado_kb": resultado["tamanho_processado_kb"],
                "dispositivo": resultado["dispositivo"]
            }
        }, status=200)

    except ServiceException as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": e.message
        }, status=e.status_code)
    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Erro interno durante processamento de super-resolução: {str(e)}"
        }, status=500)


@csrf_exempt
@requer_autenticacao
def download_imagem_view(request: HttpRequest, imagem_id: int) -> HttpResponse:
    """
    Endpoint para download direto do binário da imagem processada ou original.
    GET /api/imagens/<id>/download/?tipo=processada (ou ?tipo=original)
    """
    if request.method != 'GET':
        return JsonResponse({"status": "erro", "mensagem": "Método não permitido."}, status=405)

    imagem = Imagem.objects.filter(id=imagem_id, usuario=request.usuario).first()
    if not imagem:
        return JsonResponse({"status": "erro", "mensagem": "Imagem não encontrada."}, status=404)

    tipo = request.GET.get('tipo', 'processada')
    if tipo == 'original':
        dados = bytes(imagem.dadosOriginal)
        nome = f"original_{imagem.nomeArquivo}"
    else:
        dados = bytes(imagem.dadosProcessada) if imagem.dadosProcessada else bytes(imagem.dadosOriginal)
        nome = f"esc_sr_{imagem.nomeArquivo}"

    response = HttpResponse(dados, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{nome}"'
    return response
