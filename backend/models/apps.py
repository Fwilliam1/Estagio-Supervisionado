from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_usuario_admin_default(sender, **kwargs):
    """
    Cria automaticamente o usuário default 'admin' com a senha 'admin'
    após a execução das migrações do banco de dados.
    Garante que o usuário exista em qualquer máquina em que o backend for inicializado.
    """
    try:
        from .usuario import Usuario
        admin_nome = "admin"
        admin_email = "admin@dsr.com"

        # 1. Cria na tabela 'usuario' (Entidade do domínio)
        if not Usuario.objects.filter(nome=admin_nome).exists() and not Usuario.objects.filter(email=admin_email).exists():
            admin_user = Usuario(
                nome=admin_nome,
                email=admin_email
            )
            admin_user.set_password("admin")
            admin_user.save()
            print(f"[DSR_DB] Usuário padrão '{admin_nome}' (senha: 'admin') criado com sucesso na tabela de Usuários.")

        # 2. Cria também no auth.User do Django para permitir login no painel /admin
        from django.contrib.auth import get_user_model
        AuthUser = get_user_model()
        if not AuthUser.objects.filter(username=admin_nome).exists():
            AuthUser.objects.create_superuser(
                username=admin_nome,
                email=admin_email,
                password="admin"
            )
            print(f"[DSR_DB] Superusuário Django '{admin_nome}' criado com sucesso para o painel de administração.")

    except Exception as e:
        print(f"[DSR_DB] Aviso ao verificar/criar usuário padrão admin: {e}")


class ModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'models'
    verbose_name = 'Modelos DSR'

    def import_models(self):
        self.models = self.apps.all_models[self.label]
        from .usuario import Usuario
        from .algoritmo import Algoritmo
        from .imagem import Imagem
        self.models_module = self.module

    def ready(self):
        post_migrate.connect(criar_usuario_admin_default, sender=self)
