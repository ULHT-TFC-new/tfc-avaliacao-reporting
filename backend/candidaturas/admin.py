from django.contrib import admin

from .models import Candidatura, Grupo, Selecao


@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ["grupo", "proposta", "prioridade", "estado", "motivo_fim"]
    list_filter = ["ano_letivo", "estado"]
    search_fields = ["grupo__submissor__numero", "grupo__colega__numero", "proposta__codigo"]


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "ano_letivo", "origem", "estado"]
    list_filter = ["estado", "origem"]


@admin.register(Selecao)
class SelecaoAdmin(admin.ModelAdmin):
    list_display = ["proposta", "candidatura", "selecionada", "confirmada", "data_selecao", "data_confirmacao"]
    list_filter = ["selecionada", "confirmada"]
