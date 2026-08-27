import json
import base64
from typing import Dict, Any, Tuple
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.super_resolution_service import SuperResolutionService
from services.depth_service import DepthAnythingService
from services.dehazing_service import DehazingService
from services.exceptions import ServiceException, ValidacaoError
from .decorators import requer_autenticacao


def _extrair_imagem_e_parametros(request: HttpRequest) -> Tuple[bytes, str, int, str, Dict[str, Any]]:
    """
    Extrai bytes da imagem, nome do arquivo, escala, tipo de algoritmo e opções extras
    a partir de multipart/form-data ou JSON.
    """
    nome_arquivo = "imagem_upload.png"
    escala = 2
    tipo_algoritmo = "super-resolution"
    image_bytes = b""
    opcoes = {}

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
        opcoes = {
            'encoder': request.POST.get('encoder', 'vits'),
            'grayscale': request.POST.get('grayscale', 'true').lower() in ('true', '1', 'yes'),
            'colormap': request.POST.get('colormap', 'Spectral_r'),
            'input_size': int(request.POST.get('input_size', 518)),
        }

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
                    body.get('dadosOriginal') or
                    body.get('inputImage')
                )
                if b64_data:
                    # Remove cabeçalho data:image/...;base64, se existir
                    if ',' in b64_data:
                        b64_data = b64_data.split(',', 1)[1]
                    image_bytes = base64.b64decode(b64_data)

                nome_arquivo = body.get('nome_arquivo') or body.get('filename') or body.get('fileName') or nome_arquivo
                escala = body.get('scale') or body.get('escala') or 2
                tipo_algoritmo = body.get('algoritmo') or body.get('algorithm') or body.get('process') or "super-resolution"
                opcoes = {
                    'encoder': body.get('encoder', 'vits'),
                    'grayscale': str(body.get('grayscale', 'true')).lower() in ('true', '1', 'yes'),
                    'colormap': body.get('colormap', 'Spectral_r'),
                    'input_size': int(body.get('input_size', 518)),
                }
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            raise ValidacaoError(f"Erro ao processar dados JSON da requisição: {str(e)}")

    if not image_bytes:
        raise ValidacaoError("Nenhum arquivo ou dado de imagem foi enviado na requisição.")

    try:
        escala_int = int(escala)
    except (ValueError, TypeError):
        escala_int = 2

    return image_bytes, nome_arquivo, escala_int, tipo_algoritmo, opcoes


@csrf_exempt
@requer_autenticacao
def processamento_router_view(request: HttpRequest) -> JsonResponse:
    """
    Roteador genérico para processamento de imagem (/api/processar/).
    Encaminha para Dehazing (Depth Anything V2 + UDPNet FSNet OTS) ou Super-Resolução (ESC).
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, escala, tipo_algoritmo, opcoes = _extrair_imagem_e_parametros(request)
        if tipo_algoritmo.lower() in ('dehazing', 'desembaçamento', 'desembacamento'):
            return _executar_dehazing(request, image_bytes, nome_arquivo, opcoes)
        elif tipo_algoritmo.lower() in ('depth', 'profundidade', 'depth-anything'):
            return _executar_depth(request, image_bytes, nome_arquivo, opcoes)
        else:
            return _executar_super_resolution(request, image_bytes, nome_arquivo, escala)
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno: {str(e)}"}, status=500)


@csrf_exempt
@requer_autenticacao
def super_resolution_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para aplicar Super-Resolução com a arquitetura ESC (x2, x3, x4).
    POST /api/processar/super-resolution/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, escala, tipo_algoritmo, _ = _extrair_imagem_e_parametros(request)
        return _executar_super_resolution(request, image_bytes, nome_arquivo, escala)
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno durante super-resolução: {str(e)}"}, status=500)


def _executar_super_resolution(request: HttpRequest, image_bytes: bytes, nome_arquivo: str, escala: int) -> JsonResponse:
    resultado = SuperResolutionService.processar_imagem(
        image_bytes=image_bytes,
        scale=escala
    )

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


@csrf_exempt
@requer_autenticacao
def dehazing_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para Image Dehazing completo (Depth Anything V2 + UDPNet FSNet OTS).
    POST /api/processar/dehazing/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, _, _, opcoes = _extrair_imagem_e_parametros(request)
        return _executar_dehazing(request, image_bytes, nome_arquivo, opcoes)
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno durante dehazing: {str(e)}"}, status=500)


def _executar_dehazing(request: HttpRequest, image_bytes: bytes, nome_arquivo: str, opcoes: Dict[str, Any]) -> JsonResponse:
    input_size = opcoes.get('input_size', 518)

    resultado = DehazingService.processar_imagem(
        image_bytes=image_bytes,
        input_size=input_size
    )

    usuario = request.usuario
    algoritmo_instancia, _ = Algoritmo.objects.get_or_create(
        tipo="UDPNet_FSNet_OTS_Dehazing",
        defaults={
            "parametros": json.dumps({
                "modelo_dehazing": "UDPNet_FSNet",
                "pesos_dehazing": "FSNet_UDPNet_OTS.ckpt",
                "modelo_profundidade": "DepthAnythingV2_ViTS",
                "pesos_profundidade": "depth_anything_v2_vits.pth",
                "input_size": input_size
            })
        }
    )

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
        "mensagem": "Image Dehazing aplicado com sucesso via Depth Anything V2 + UDPNet (FSNet OTS)!",
        "dados": {
            "imagem_id": registro_imagem.id,
            "nome_arquivo": nome_arquivo,
            "imagem_base64": resultado["imagem_processada_base64"],
            "mapa_profundidade_base64": resultado.get("mapa_profundidade_base64"),
            "resolucao_original": resultado["resolucao_original"],
            "resolucao_processada": resultado["resolucao_processada"],
            "largura_original": resultado["largura_original"],
            "altura_original": resultado["altura_original"],
            "largura_processada": resultado["largura_processada"],
            "altura_processada": resultado["altura_processada"],
            "modelo_dehazing": resultado["modelo_dehazing"],
            "modelo_profundidade": resultado["modelo_profundidade"],
            "tempo_execucao_segundos": resultado["tempo_execucao_segundos"],
            "tamanho_original_kb": resultado["tamanho_original_kb"],
            "tamanho_processado_kb": resultado["tamanho_processado_kb"],
            "dispositivo": resultado["dispositivo"]
        }
    }, status=200)


@csrf_exempt
@requer_autenticacao
def depth_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para inferência direta do Mapa de Profundidade via Depth Anything V2.
    POST /api/processar/depth/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, _, _, opcoes = _extrair_imagem_e_parametros(request)
        return _executar_depth(request, image_bytes, nome_arquivo, opcoes)
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno durante estimativa de profundidade: {str(e)}"}, status=500)


def _executar_depth(request: HttpRequest, image_bytes: bytes, nome_arquivo: str, opcoes: Dict[str, Any]) -> JsonResponse:
    encoder = opcoes.get('encoder', 'vits')
    grayscale = opcoes.get('grayscale', True)
    colormap = opcoes.get('colormap', 'Spectral_r')
    input_size = opcoes.get('input_size', 518)

    resultado = DepthAnythingService.processar_imagem(
        image_bytes=image_bytes,
        encoder=encoder,
        grayscale=grayscale,
        colormap=colormap,
        input_size=input_size
    )

    usuario = request.usuario
    algoritmo_instancia, _ = Algoritmo.objects.get_or_create(
        tipo=f"DepthAnythingV2_{encoder.upper()}_DepthMap",
        defaults={
            "parametros": json.dumps({
                "modelo": "DepthAnythingV2",
                "encoder": encoder,
                "input_size": input_size,
                "grayscale": grayscale,
                "colormap": colormap,
                "pesos": f"depth_anything_v2_{encoder}.pth"
            })
        }
    )

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
        "mensagem": f"Mapa de profundidade gerado com sucesso via Depth Anything V2 ({encoder})!",
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
            "encoder": resultado["encoder"],
            "profundidade_min": resultado["profundidade_min"],
            "profundidade_max": resultado["profundidade_max"],
            "tempo_execucao_segundos": resultado["tempo_execucao_segundos"],
            "tamanho_original_kb": resultado["tamanho_original_kb"],
            "tamanho_processado_kb": resultado["tamanho_processado_kb"],
            "dispositivo": resultado["dispositivo"]
        }
    }, status=200)



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
        nome = f"processada_{imagem.nomeArquivo}"

    response = HttpResponse(dados, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{nome}"'
    return response

