from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    senha_hash = models.CharField(max_length=255)
    token_versao = models.CharField(max_length=64, default='', blank=True, verbose_name='Versão do Token Ativo')

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def set_password(self, raw_password: str) -> None:
        """Gera o hash da senha e armazena em senha_hash."""
        self.senha_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verifica se a senha em texto puro corresponde ao hash armazenado."""
        return check_password(raw_password, self.senha_hash)

    def __str__(self):
        return f"{self.nome} <{self.email}>"
