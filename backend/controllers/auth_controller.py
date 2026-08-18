import json
from typing import Dict, Any
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from services.auth_service import AuthService
from services.usuario_service import UsuarioService
from services.exceptions import (
    ServiceException,
    ValidacaoError,
    UsuarioJaExisteError,
    CredenciaisInvalidasError,
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
def cadastrar_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint público para cadastro de novo usuário.
    POST /api/auth/cadastrar/ ou POST /api/cadastrar/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para cadastrar."
        }, status=405)

    try:
        body = _parse_body(request)
        nome = body.get('nome') or body.get('name')
        email = body.get('email')
        senha = body.get('senha') or body.get('password')
        confirmacao = (
            body.get('confirmacao_senha') or
            body.get('confirmPassword') or
            body.get('confirm_password') or
            body.get('confirmacaoSenha')
        )

        resultado = AuthService.cadastrar(
            nome=nome,
            email=email,
            senha=senha,
            confirmacao_senha=confirmacao
        )

        return JsonResponse({
            "status": "sucesso",
            "mensagem": resultado["mensagem"],
            "dados": resultado["usuario"]
        }, status=201)

    except ServiceException as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": e.message
        }, status=e.status_code)
    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Erro interno ao realizar cadastro: {str(e)}"
        }, status=500)


@csrf_exempt
def login_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint público para autenticação de usuário (Login).
    Retorna o token JWT (válido por 2h) e invalida qualquer sessão anterior.
    POST /api/auth/login/ ou POST /api/login/
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido. Utilize POST para efetuar login."
        }, status=405)

    try:
        body = _parse_body(request)
        email = body.get('email')
        senha = body.get('senha') or body.get('password')

        resultado_auth = AuthService.autenticar(email=email, senha=senha)
        usuario = resultado_auth["usuario"]

        # Salva na sessão Django se disponível
        if hasattr(request, 'session'):
            request.session['usuario_id'] = usuario.id
            request.session['usuario_email'] = usuario.email
            request.session['usuario_nome'] = usuario.nome

        dados_usuario = UsuarioService.usuario_to_dict(usuario)

        return JsonResponse({
            "status": "sucesso",
            "mensagem": "Login realizado com sucesso.",
            "token": resultado_auth["token"],
            "tipo_token": resultado_auth["tipo_token"],
            "expira_em_segundos": resultado_auth["expira_em_segundos"],
            "expira_em": resultado_auth["expira_em"],
            "dados": dados_usuario
        }, status=200)

    except ServiceException as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": e.message
        }, status=e.status_code)
    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Erro interno ao realizar login: {str(e)}"
        }, status=500)


@csrf_exempt
@requer_autenticacao
def logout_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint para encerrar a sessão e invalidar o token JWT do usuário.
    POST /api/auth/logout/ ou POST /api/logout/
    Requer cabeçalho 'Authorization: Bearer <token>'
    """
    try:
        if hasattr(request, 'usuario') and request.usuario:
            AuthService.logout(request.usuario)

        if hasattr(request, 'session'):
            request.session.flush()

        return JsonResponse({
            "status": "sucesso",
            "mensagem": "Logout realizado com sucesso. Token invalidado."
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Erro ao realizar logout: {str(e)}"
        }, status=500)


@csrf_exempt
@requer_autenticacao
def me_view(request: HttpRequest) -> JsonResponse:
    """
    Endpoint protegido para obter os dados do usuário autenticado no token JWT.
    GET /api/auth/me/ ou GET /api/me/
    Requer cabeçalho 'Authorization: Bearer <token>'
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "erro",
            "mensagem": f"Método {request.method} não permitido."
        }, status=405)

    dados_usuario = UsuarioService.usuario_to_dict(request.usuario)
    return JsonResponse({
        "status": "sucesso",
        "dados": dados_usuario
    }, status=200)

