from django.db import models
from .usuario import Usuario
from .algoritmo import Algoritmo


class Imagem(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='imagens',
        db_column='usuario_id',
        verbose_name='Usuário'
    )
    algoritmo = models.ForeignKey(
        Algoritmo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imagens',
        db_column='algoritmo_id',
        verbose_name='Algoritmo'
    )
    nomeArquivo = models.CharField(max_length=255, db_column='nomeArquivo', verbose_name='Nome do Arquivo')
    formato = models.CharField(max_length=50, verbose_name='Formato')
    resolucao = models.CharField(max_length=50, verbose_name='Resolução')
    tamanho = models.FloatField(verbose_name='Tamanho', help_text='Tamanho do arquivo em KB ou MB')
    dadosOriginal = models.BinaryField(db_column='dadosOriginal', verbose_name='Dados Original (Blob)')
    dadosProcessada = models.BinaryField(null=True, blank=True, db_column='dadosProcessada', verbose_name='Dados Processada (Blob)')
    criado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='Criado em')

    class Meta:
        db_table = 'imagem'
        verbose_name = 'Imagem'
        verbose_name_plural = 'Imagens'
        ordering = ['-id']

    def __str__(self):
        return f"{self.nomeArquivo} (ID: {self.id})"
