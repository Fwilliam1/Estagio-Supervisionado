from django.contrib import admin
from django.urls import path
from models import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # REST API Endpoints para Frontend React
    path('api/login/', views.login_api, name='api_login'),
    path('api/cadastro/', views.cadastro_api, name='api_cadastro'),
    path('api/imagens/historico/', views.historico_api, name='api_historico'),
    path('api/imagens/salvar/', views.salvar_imagem_api, name='api_salvar_imagem'),
    path('api/imagens/<int:imagem_id>/', views.excluir_imagem_api, name='api_excluir_imagem'),
    path('api/imagens/limpar/', views.limpar_historico_api, name='api_limpar_historico'),
]
