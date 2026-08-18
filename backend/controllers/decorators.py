from functools import wraps
from django.http import JsonResponse, HttpRequest
from services.jwt_service import JWTService
from services.exceptions import ServiceException


def requer_autenticacao(view_func):
    """
    Decorator que protege rotas exigindo um token JWT válido no cabeçalho:
    Authorization: Bearer <token>

    Injeta o objeto 'usuario' autenticado em 'request.usuario'.
    Retorna status 401 Unauthorized se o token for inválido, ausente,
    expirado (> 2 horas) ou invalidado por um novo login do mesmo usuário.
    """
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args, **kwargs):
        # 1. Tenta obter o cabeçalho Authorization
        auth_header = (
            request.headers.get('Authorization') or
            request.META.get('HTTP_AUTHORIZATION') or
            request.GET.get('token')
        )

        if not auth_header:
            return JsonResponse({
                "status": "erro",
                "mensagem": "Acesso não autorizado. Envie o cabeçalho 'Authorization: Bearer <token>'."
            }, status=401)

        try:
            # 2. Valida o token JWT e verifica versão de sessão
            usuario = JWTService.validar_token(auth_header)
            request.usuario = usuario
            request.usuario_id = usuario.id
        except ServiceException as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": e.message
            }, status=e.status_code)
        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Erro na validação do token: {str(e)}"
            }, status=401)

        return view_func(request, *args, **kwargs)

    return _wrapped_view
