import io
import json
import base64
from typing import Dict, Any, Tuple
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from models.imagem import Imagem
from models.algoritmo import Algoritmo
from services.hdr_service import HDRService
from services.super_resolution_service import SuperResolutionService
from services.depth_service import DepthAnythingService
from services.dehazing_service import DehazingService
from services.convir_service import ConvIRService
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
        modelo_param = request.POST.get('modelo') or request.POST.get('model')
        if not modelo_param:
            if 'convir' in tipo_algoritmo.lower():
                modelo = 'convir'
            elif tipo_algoritmo.lower() in ('dehazing', 'desembaçamento', 'desembacamento'):
                modelo = 'udpnet'
            elif 'esc' in tipo_algoritmo.lower():
                modelo = 'ESC'
            else:
                modelo = 'DMNet'
        else:
            modelo = modelo_param

        tone_mapping = (
            request.POST.get('tone_mapping') or
            request.POST.get('toneMapping') or
            request.POST.get('tonemap') or
            request.POST.get('tipo_tone_mapping') or
            'reinhard'
        )

        opcoes = {
            'modelo': modelo,
            'version': request.POST.get('version') or request.POST.get('versao') or 'small',
            'encoder': request.POST.get('encoder', 'vits'),
            'grayscale': request.POST.get('grayscale', 'true').lower() in ('true', '1', 'yes'),
            'colormap': request.POST.get('colormap', 'Spectral_r'),
            'input_size': int(request.POST.get('input_size', 518)),
            'clip_limit': float(request.POST.get('clip_limit', 2.5)),
            'tile_grid_size': int(request.POST.get('tile_grid_size', 8)),
            'tone_mapping': tone_mapping,
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
                modelo_param = body.get('modelo') or body.get('model')
                if not modelo_param:
                    if 'convir' in tipo_algoritmo.lower():
                        modelo = 'convir'
                    elif tipo_algoritmo.lower() in ('dehazing', 'desembaçamento', 'desembacamento'):
                        modelo = 'udpnet'
                    elif 'esc' in tipo_algoritmo.lower():
                        modelo = 'ESC'
                    else:
                        modelo = 'DMNet'
                else:
                    modelo = modelo_param

                tone_mapping = (
                    body.get('tone_mapping') or
                    body.get('toneMapping') or
                    body.get('tonemap') or
                    body.get('tipo_tone_mapping') or
                    'reinhard'
                )

                opcoes = {
                    'modelo': modelo,
                    'version': body.get('version') or body.get('versao') or 'small',
                    'encoder': body.get('encoder', 'vits'),
                    'grayscale': str(body.get('grayscale', 'true')).lower() in ('true', '1', 'yes'),
                    'colormap': body.get('colormap', 'Spectral_r'),
                    'input_size': int(body.get('input_size', 518)),
                    'clip_limit': float(body.get('clip_limit', 2.5)),
                    'tile_grid_size': int(body.get('tile_grid_size', 8)),
                    'tone_mapping': tone_mapping,
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
    Encaminha para Dehazing (Depth Anything V2 + UDPNet FSNet OTS ou ConvIR), Depth ou Super-Resolução (DMNet ou ESC).
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
        elif tipo_algoritmo.lower() in ('convir', 'convir_small', 'convir-small'):
            opcoes['modelo'] = 'convir'
            return _executar_dehazing(request, image_bytes, nome_arquivo, opcoes)
        elif tipo_algoritmo.lower() in ('depth', 'profundidade', 'depth-anything'):
            return _executar_depth(request, image_bytes, nome_arquivo, opcoes)
        elif tipo_algoritmo.lower() in ('hdr', 'safhdr'):
            return _executar_hdr(request, image_bytes, nome_arquivo, opcoes)
        else:
            return _executar_super_resolution(request, image_bytes, nome_arquivo, escala, opcoes.get('modelo', 'DMNet'))
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno: {str(e)}"}, status=500)


@csrf_exempt
@requer_autenticacao
def super_resolution_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para aplicar Super-Resolução com as arquiteturas DMNet ou ESC (x2, x3, x4).
    POST /api/processar/super-resolution/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, escala, tipo_algoritmo, opcoes = _extrair_imagem_e_parametros(request)
        return _executar_super_resolution(request, image_bytes, nome_arquivo, escala, opcoes.get('modelo', 'DMNet'))
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno durante super-resolução: {str(e)}"}, status=500)


def _executar_super_resolution(
    request: HttpRequest,
    image_bytes: bytes,
    nome_arquivo: str,
    escala: int,
    modelo: str = 'DMNet'
) -> JsonResponse:
    modelo_norm = SuperResolutionService.normalizar_nome_modelo(modelo)
    modelo_display = 'DMNet' if modelo_norm == 'dmnet' else 'ESC'

    resultado = SuperResolutionService.processar_imagem(
        image_bytes=image_bytes,
        scale=escala,
        model_name=modelo_display
    )

    usuario = request.usuario
    pesos_nome = f"DMNet_X{escala}.pth" if modelo_norm == 'dmnet' else f"ESC_DIV2K_X{escala}.pth"
    algoritmo_instancia, _ = Algoritmo.objects.get_or_create(
        tipo=f"{modelo_display}_SuperResolution_X{escala}",
        defaults={
            "parametros": json.dumps({
                "modelo": modelo_display,
                "escala": escala,
                "pesos": pesos_nome,
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
        "mensagem": f"Super-resolução {escala}x aplicada com sucesso via rede {modelo_display}!",
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
            "modelo": resultado["modelo"],
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
    modelo = str(opcoes.get('modelo') or opcoes.get('model') or 'udpnet').lower()
    version = str(opcoes.get('version') or opcoes.get('versao') or 'small')

    if modelo in ('convir', 'convir_small', 'convir-small', 'convir_ots'):
        resultado = ConvIRService.processar_imagem(
            image_bytes=image_bytes,
            version=version
        )
        tipo_algoritmo_str = f"ConvIR_{version}_OTS_Dehazing"
        algoritmo_params = {
            "modelo": "ConvIR",
            "versao": version,
            "pesos": "ots_small.pkl",
            "dataset_treino": "RESIDE-OTS"
        }
        msg_sucesso = f"Image Dehazing aplicado com sucesso via ConvIR ({version}, pesos ots_small.pkl)!"
    else:
        input_size = opcoes.get('input_size', 518)
        resultado = DehazingService.processar_imagem(
            image_bytes=image_bytes,
            input_size=input_size
        )
        tipo_algoritmo_str = "UDPNet_FSNet_OTS_Dehazing"
        algoritmo_params = {
            "modelo_dehazing": "UDPNet_FSNet",
            "pesos_dehazing": "FSNet_UDPNet_OTS.ckpt",
            "modelo_profundidade": "DepthAnythingV2_ViTS",
            "pesos_profundidade": "depth_anything_v2_vits.pth",
            "input_size": input_size
        }
        msg_sucesso = "Image Dehazing aplicado com sucesso via Depth Anything V2 + UDPNet (FSNet OTS)!"

    usuario = request.usuario
    algoritmo_instancia, _ = Algoritmo.objects.get_or_create(
        tipo=tipo_algoritmo_str,
        defaults={
            "parametros": json.dumps(algoritmo_params)
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
        "mensagem": msg_sucesso,
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
            "modelo_profundidade": resultado.get("modelo_profundidade"),
            "tempo_execucao_segundos": resultado["tempo_execucao_segundos"],
            "tamanho_original_kb": resultado["tamanho_original_kb"],
            "tamanho_processado_kb": resultado["tamanho_processado_kb"],
            "dispositivo": resultado["dispositivo"]
        }
    }, status=200)


@csrf_exempt
@requer_autenticacao
def convir_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint dedicado para Image Dehazing com ConvIR (small, pesos ots_small.pkl).
    POST /api/processar/convir/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, _, _, opcoes = _extrair_imagem_e_parametros(request)
        opcoes['modelo'] = 'convir'
        return _executar_dehazing(request, image_bytes, nome_arquivo, opcoes)
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno durante dehazing ConvIR: {str(e)}"}, status=500)


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





from services.hdr_service import HDRService

@csrf_exempt
@requer_autenticacao
def hdr_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para processamento HDR e Tone Mapping (SAFHDR).
    POST /api/processar/hdr/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para processar."
        }, status=405)

    try:
        image_bytes, nome_arquivo, _, _, opcoes = _extrair_imagem_e_parametros(request)
        return _executar_hdr(request, image_bytes, nome_arquivo, opcoes)
    except ServiceException as e:
        return JsonResponse({"status": "erro", "mensagem": e.message}, status=e.status_code)
    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": f"Erro interno durante processamento HDR: {str(e)}"}, status=500)


def _executar_hdr(request: HttpRequest, image_bytes: bytes, nome_arquivo: str, opcoes: Dict[str, Any]) -> JsonResponse:

    # Extrai parâmetros opcionais, caso enviados no POST
    clip_limit = float(opcoes.get('clip_limit', 2.5))
    tile_grid_size = int(opcoes.get('tile_grid_size', 8))
    tone_mapping = (
        opcoes.get('tone_mapping') or
        opcoes.get('toneMapping') or
        opcoes.get('tonemap') or
        'reinhard'
    )

    # Chama o serviço
    resultado = HDRService.processar_imagem(
        image_bytes=image_bytes,
        clip_limit=clip_limit,
        tile_grid_size=tile_grid_size,
        tone_mapping=tone_mapping
    )

    tm_aplicado = resultado.get("tone_mapping", str(tone_mapping).capitalize())

    # Configuração dos metadados para salvar no banco
    tipo_algoritmo_str = f"SAFHDR_{tm_aplicado}_ToneMapping"
    algoritmo_params = {
        "modelo": "SAFHDR",
        "pesos": "model_tm_406392_G.pth",
        "tone_mapping": tm_aplicado,
        "mu_law": 5000.0,
        "clip_limit": clip_limit,
        "tile_grid_size": tile_grid_size
    }
    msg_sucesso = f"Processamento HDR ({tm_aplicado}) aplicado com sucesso via SAFHDR!"

    # Tratamento do formato da imagem
    formato = "PNG"
    if "." in nome_arquivo:
        formato_extraido = nome_arquivo.rsplit(".", 1)[-1].upper()
        formato = "JPEG" if formato_extraido == "JPG" else formato_extraido

    # Garante compatibilidade de Data URI e bytes para retorno e persistência
    b64_val = resultado.get("imagem_processada_base64", "")
    if not b64_val.startswith("data:image/"):
        img_bytes = resultado.get("imagem_processada_bytes")
        if not img_bytes and "imagem_tonemapped" in resultado:
            img_pil = resultado["imagem_tonemapped"]
            buffer = io.BytesIO()
            img_pil.save(buffer, format=formato if formato in ["PNG", "JPEG"] else "PNG")
            img_bytes = buffer.getvalue()
            resultado["imagem_processada_bytes"] = img_bytes

        if img_bytes:
            raw_b64 = base64.b64encode(img_bytes).decode('utf-8')
            fmt_prefix = "jpeg" if formato.upper() in ["JPEG", "JPG"] else "png"
            resultado["imagem_processada_base64"] = f"data:image/{fmt_prefix};base64,{raw_b64}"

    orig_w = resultado.get("largura_original")
    orig_h = resultado.get("altura_original")
    if orig_w is None or orig_h is None:
        if "dimensoes_originais" in resultado:
            orig_w, orig_h = resultado["dimensoes_originais"]
        else:
            orig_w, orig_h = 0, 0

    proc_w = resultado.get("largura_processada", orig_w)
    proc_h = resultado.get("altura_processada", orig_h)
    resultado["resolucao_original"] = resultado.get("resolucao_original", f"{orig_w}x{orig_h}")
    resultado["resolucao_processada"] = resultado.get("resolucao_processada", f"{proc_w}x{proc_h}")
    resultado["tamanho_original_kb"] = resultado.get("tamanho_original_kb", round(len(image_bytes) / 1024, 2))
    resultado["tamanho_processado_kb"] = resultado.get("tamanho_processado_kb", round(len(resultado.get("imagem_processada_bytes", b"")) / 1024, 2))
    resultado["tempo_execucao_segundos"] = resultado.get("tempo_execucao_segundos", resultado.get("tempo_processamento", 0.0))

    # Registro no Banco de Dados
    usuario = request.usuario
    algoritmo_instancia, _ = Algoritmo.objects.get_or_create(
        tipo=tipo_algoritmo_str,
        defaults={
            "parametros": json.dumps(algoritmo_params)
        }
    )

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

    # Retorno padrão da API
    return JsonResponse({
        "status": "sucesso",
        "mensagem": msg_sucesso,
        "dados": {
            "imagem_id": registro_imagem.id,
            "nome_arquivo": nome_arquivo,
            "imagem_base64": resultado["imagem_processada_base64"],
            "resolucao_original": resultado["resolucao_original"],
            "resolucao_processada": resultado["resolucao_processada"],
            "largura_original": orig_w,
            "altura_original": orig_h,
            "largura_processada": proc_w,
            "altura_processada": proc_h,
            "tempo_execucao_segundos": resultado["tempo_execucao_segundos"],
            "tamanho_original_kb": resultado["tamanho_original_kb"],
            "modelo": f"SAFHDR ({tm_aplicado})",
            "modelo_hdr": "SAFHDR",
            "tone_mapping": tm_aplicado,
            "dispositivo": resultado.get("dispositivo", "CPU")
        }
    }, status=200)