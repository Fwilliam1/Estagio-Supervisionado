from django.db import models


class Algoritmo(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=100)
    parametros = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'algoritmo'
        verbose_name = 'Algoritmo'
        verbose_name_plural = 'Algoritmos'

    def __str__(self):
        return f"Algoritmo {self.tipo} (ID: {self.id})"
