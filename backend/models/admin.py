from django.contrib import admin
from .usuario import Usuario
from .algoritmo import Algoritmo
from .imagem import Imagem


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'email')
    search_fields = ('nome', 'email')


@admin.register(Algoritmo)
class AlgoritmoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'parametros')
    search_fields = ('tipo',)


@admin.register(Imagem)
class ImagemAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomeArquivo', 'formato', 'resolucao', 'tamanho', 'usuario', 'algoritmo')
    list_filter = ('formato', 'usuario', 'algoritmo')
    search_fields = ('nomeArquivo',)
