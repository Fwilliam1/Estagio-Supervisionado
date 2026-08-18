import base64
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .usuario import Usuario
from .imagem import Imagem
from .algoritmo import Algoritmo


def helper_data_url_to_bytes(data_url: str):
    """Converte uma string DataURL (data:image/...;base64,...) em bytes brutos."""
    if not data_url:
        return None
    if ',' in data_url:
        _, encoded = data_url.split(',', 1)
    else:
        encoded = data_url
    try:
        return base64.b64decode(encoded)
    except Exception:
        return encoded.encode('utf-8')


def helper_bytes_to_data_url(raw_bytes: bytes, mime_type: str = 'image/png') -> str:
    """Converte bytes brutos em uma string DataURL pronta para visualização no navegador."""
    if not raw_bytes:
        return None
    try:
        if isinstance(raw_bytes, memoryview):
            raw_bytes = raw_bytes.tobytes()
        elif isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode('utf-8')
            
        b64_str = base64.b64encode(raw_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{b64_str}"
    except Exception:
        return None


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login_api(request):
    """Endpoint para autenticar o usuário."""
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email:
            return JsonResponse({"success": False, "error": "E-mail é obrigatório"}, status=400)

        usuario = Usuario.objects.filter(email=email).first()
        if not usuario:
            # Cria automaticamente usuário se não existir (para facilidade de uso)
            nome = email.split('@')[0].capitalize()
            usuario = Usuario(nome=nome, email=email)
            usuario.set_password(password or '123456')
            usuario.save()

        return JsonResponse({
            "success": True,
            "user": {
                "id": usuario.id,
                "name": usuario.nome,
                "email": usuario.email,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def cadastro_api(request):
    """Endpoint para registrar novo usuário."""
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    try:
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email:
            return JsonResponse({"success": False, "error": "E-mail é obrigatório"}, status=400)

        usuario = Usuario.objects.filter(email=email).first()
        if usuario:
            if name:
                usuario.nome = name
            if password:
                usuario.set_password(password)
            usuario.save()
        else:
            usuario = Usuario(
                nome=name or email.split('@')[0].capitalize(),
                email=email
            )
            usuario.set_password(password or '123456')
            usuario.save()

        return JsonResponse({
            "success": True,
            "user": {
                "id": usuario.id,
                "name": usuario.nome,
                "email": usuario.email,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def historico_api(request):
    """Endpoint para buscar o histórico de imagens de um usuário específico."""
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    email = request.GET.get('email', '').strip().lower()
    if not email:
        return JsonResponse({"success": False, "error": "Parâmetro email é obrigatório"}, status=400)

    try:
        usuario = Usuario.objects.filter(email=email).first()
        if not usuario:
            return JsonResponse({"success": True, "history": []})

        imagens = Imagem.objects.filter(usuario=usuario).select_related('algoritmo')

        history_list = []
        for img in imagens:
            formato = img.formato or 'image/png'
            input_url = helper_bytes_to_data_url(img.dadosOriginal, formato)
            processed_url = helper_bytes_to_data_url(img.dadosProcessada, formato) if img.dadosProcessada else None

            created_time = img.criado_em or timezone.now()
            formatted_date = created_time.strftime("%d/%m/%Y")
            formatted_time = created_time.strftime("%H:%M:%S")

            algo_tipo = img.algoritmo.tipo if img.algoritmo else 'dehazing'
            algo_label = "Super-Resolution" if algo_tipo == 'super-resolution' else "Image Dehazing"

            file_size_formatted = f"{img.tamanho:.2f} MB" if img.tamanho else "1.0 MB"

            history_list.append({
                "id": f"db_{img.id}",
                "db_id": img.id,
                "userEmail": usuario.email,
                "date": formatted_date,
                "time": formatted_time,
                "timestamp": int(created_time.timestamp() * 1000),
                "inputImage": input_url,
                "processedImage": processed_url,
                "process": algo_tipo,
                "processLabel": algo_label,
                "fileName": img.nomeArquivo,
                "fileSize": file_size_formatted,
                "fileSizeInBytes": int((img.tamanho or 1.0) * 1024 * 1024),
                "dimensions": img.resolucao,
            })

        return JsonResponse({
            "success": True,
            "history": history_list
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def salvar_imagem_api(request):
    """Endpoint para salvar um novo processamento de imagem no banco de dados."""
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    try:
        data = json.loads(request.body.decode('utf-8'))
        email = data.get('email', '').strip().lower()
        input_image_str = data.get('inputImage')
        processed_image_str = data.get('processedImage')
        process_type = data.get('process', 'dehazing')
        file_name = data.get('fileName', 'imagem_processada.png')
        file_size = data.get('fileSize', '1.0 MB')
        dimensions = data.get('dimensions', '1920x1080')
        formato = data.get('formato', 'image/png')

        if not email or not input_image_str:
            return JsonResponse({
                "success": False,
                "error": "Email e inputImage são obrigatórios."
            }, status=400)

        # 1. Encontra ou cria o Usuário
        usuario, _ = Usuario.objects.get_or_create(
            email=email,
            defaults={'nome': email.split('@')[0].capitalize(), 'senha_hash': 'default'}
        )

        # 2. Encontra ou cria o Algoritmo
        algoritmo, _ = Algoritmo.objects.get_or_create(
            tipo=process_type,
            defaults={'parametros': '{}'}
        )

        # 3. Extrai os bytes das imagens
        dados_original = helper_data_url_to_bytes(input_image_str)
        dados_processada = helper_data_url_to_bytes(processed_image_str) if processed_image_str else None

        # 4. Converte tamanho para float (MB)
        tamanho_mb = 1.0
        if isinstance(file_size, (int, float)):
            tamanho_mb = float(file_size) / (1024 * 1024)
        elif isinstance(file_size, str):
            try:
                clean_size = file_size.replace('MB', '').replace('KB', '').strip()
                tamanho_mb = float(clean_size)
                if 'KB' in file_size:
                    tamanho_mb = tamanho_mb / 1024
            except Exception:
                tamanho_mb = 1.0

        # 5. Salva a Imagem no banco de dados
        imagem = Imagem.objects.create(
            usuario=usuario,
            algoritmo=algoritmo,
            nomeArquivo=file_name,
            formato=formato,
            resolucao=dimensions or 'Auto',
            tamanho=round(tamanho_mb, 2),
            dadosOriginal=dados_original,
            dadosProcessada=dados_processada,
        )

        created_time = imagem.criado_em or timezone.now()

        return JsonResponse({
            "success": True,
            "item": {
                "id": f"db_{imagem.id}",
                "db_id": imagem.id,
                "userEmail": usuario.email,
                "date": created_time.strftime("%d/%m/%Y"),
                "time": created_time.strftime("%H:%M:%S"),
                "timestamp": int(created_time.timestamp() * 1000),
                "process": process_type,
                "processLabel": "Super-Resolution" if process_type == 'super-resolution' else "Image Dehazing",
                "fileName": imagem.nomeArquivo,
                "fileSize": f"{imagem.tamanho:.2f} MB",
                "dimensions": imagem.resolucao,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE", "POST", "OPTIONS"])
def excluir_imagem_api(request, imagem_id):
    """Endpoint para excluir uma imagem específica do banco de dados."""
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    try:
        Imagem.objects.filter(id=imagem_id).delete()
        return JsonResponse({"success": True, "message": "Imagem removida com sucesso."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE", "POST", "OPTIONS"])
def limpar_historico_api(request):
    """Endpoint para limpar todo o histórico de um usuário específico."""
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    try:
        if request.method == "POST":
            data = json.loads(request.body.decode('utf-8'))
            email = data.get('email', '').strip().lower()
        else:
            email = request.GET.get('email', '').strip().lower()

        if not email:
            return JsonResponse({"success": False, "error": "E-mail é obrigatório"}, status=400)

        usuario = Usuario.objects.filter(email=email).first()
        if usuario:
            Imagem.objects.filter(usuario=usuario).delete()

        return JsonResponse({"success": True, "message": "Histórico limpo com sucesso."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
