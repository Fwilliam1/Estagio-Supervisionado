import json
from typing import Dict, Any
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from services.usuario_service import UsuarioService
from services.exceptions import (
    ServiceException,
    ValidacaoError,
    UsuarioJaExisteError,
    UsuarioNaoEncontradoError,
)
from .decorators import requer_autenticacao


def _parse_body(request: HttpRequest) -> Dict[str, Any]:
    """Extrai os dados da requisição seja JSON ou Form Data."""
    if request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    if request.POST:
        return request.POST.dict()
    return {}


@csrf_exempt
@requer_autenticacao
def usuarios_collection(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para listar todos os usuários (GET) ou criar um novo usuário (POST).
    GET  /api/usuarios/
    POST /api/usuarios/
    """
    if request.method == 'GET':
        try:
            usuarios = UsuarioService.listar_usuarios()
            return JsonResponse({
                "status": "sucesso",
                "quantidade": len(usuarios),
                "dados": usuarios
            }, status=200)
        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Erro interno ao listar usuários: {str(e)}"
            }, status=500)

    elif request.method == 'POST':
        try:
            body = _parse_body(request)
            nome = body.get('nome') or body.get('name')
            email = body.get('email')
            senha = body.get('senha') or body.get('password')

            usuario = UsuarioService.criar_usuario(nome=nome, email=email, senha=senha)
            return JsonResponse({
                "status": "sucesso",
                "mensagem": "Usuário criado com sucesso.",
                "dados": UsuarioService.usuario_to_dict(usuario)
            }, status=201)

        except ServiceException as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": e.message
            }, status=e.status_code)
        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Erro interno ao criar usuário: {str(e)}"
            }, status=500)

    return JsonResponse({
        "status": "erro",
        "mensagem": f"Método {request.method} não permitido."
    }, status=405)


@csrf_exempt
@requer_autenticacao
def usuario_detail(request: HttpRequest, usuario_id: int) -> JsonResponse:
    """
    Endpoint para detalhar (GET), atualizar (PUT/PATCH) ou deletar (DELETE) um usuário por ID.
    GET    /api/usuarios/<id>/
    PUT    /api/usuarios/<id>/
    PATCH  /api/usuarios/<id>/
    DELETE /api/usuarios/<id>/
    """
    if request.method == 'GET':
        try:
            usuario = UsuarioService.obter_usuario_por_id(usuario_id)
            return JsonResponse({
                "status": "sucesso",
                "dados": UsuarioService.usuario_to_dict(usuario)
            }, status=200)
        except ServiceException as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": e.message
            }, status=e.status_code)
        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Erro interno ao obter usuário: {str(e)}"
            }, status=500)

    elif request.method in ('PUT', 'PATCH'):
        try:
            body = _parse_body(request)
            nome = body.get('nome') if 'nome' in body else body.get('name')
            email = body.get('email')
            senha = body.get('senha') if 'senha' in body else body.get('password')

            usuario = UsuarioService.atualizar_usuario(
                usuario_id=usuario_id,
                nome=nome,
                email=email,
                senha=senha
            )
            return JsonResponse({
                "status": "sucesso",
                "mensagem": "Usuário atualizado com sucesso.",
                "dados": UsuarioService.usuario_to_dict(usuario)
            }, status=200)

        except ServiceException as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": e.message
            }, status=e.status_code)
        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Erro interno ao atualizar usuário: {str(e)}"
            }, status=500)

    elif request.method == 'DELETE':
        try:
            UsuarioService.deletar_usuario(usuario_id)
            return JsonResponse({
                "status": "sucesso",
                "mensagem": f"Usuário {usuario_id} deletado com sucesso."
            }, status=200)
        except ServiceException as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": e.message
            }, status=e.status_code)
        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Erro interno ao deletar usuário: {str(e)}"
            }, status=500)

    return JsonResponse({
        "status": "erro",
        "mensagem": f"Método {request.method} não permitido."
    }, status=405)
