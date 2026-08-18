from django.urls import path
from . import usuario_controller, auth_controller

urlpatterns = [
    # Endpoints de Autenticação / Login
    path('auth/cadastrar/', auth_controller.cadastrar_view, name='api_auth_cadastrar'),
    path('auth/login/', auth_controller.login_view, name='api_auth_login'),
    path('auth/logout/', auth_controller.logout_view, name='api_auth_logout'),
    path('auth/me/', auth_controller.me_view, name='api_auth_me'),

    # Atalhos diretos para cadastro e login
    path('cadastrar/', auth_controller.cadastrar_view, name='api_cadastrar'),
    path('login/', auth_controller.login_view, name='api_login'),
    path('logout/', auth_controller.logout_view, name='api_logout'),
    path('me/', auth_controller.me_view, name='api_me'),

    # Endpoints do CRUD de Usuários
    path('usuarios/', usuario_controller.usuarios_collection, name='api_usuarios_collection'),
    path('usuarios/<int:usuario_id>/', usuario_controller.usuario_detail, name='api_usuario_detail'),
]
