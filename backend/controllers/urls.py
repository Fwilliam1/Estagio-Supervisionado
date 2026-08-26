from django.urls import path
from . import usuario_controller, auth_controller, processamento_controller
from models import views as history_views

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

    # Endpoints de Processamento de Imagens (Super-Resolução ESC)
    path('processar/super-resolution/', processamento_controller.super_resolution_view, name='api_super_resolution'),
    path('processar/', processamento_controller.super_resolution_view, name='api_processar'),
    path('imagens/<int:imagem_id>/download/', processamento_controller.download_imagem_view, name='api_download_imagem'),

    # Endpoints de Histórico de Imagens
    path('imagens/historico/', history_views.historico_api, name='api_historico'),
    path('imagens/salvar/', history_views.salvar_imagem_api, name='api_salvar_imagem'),
    path('imagens/<int:imagem_id>/', history_views.excluir_imagem_api, name='api_excluir_imagem'),
    path('imagens/limpar/', history_views.limpar_historico_api, name='api_limpar_historico'),
]

