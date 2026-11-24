"""Candidaturas e atribuição (MP-03). Ver docs/03_modelo_de_dados.md, secção 3.3.

As regras da lista de candidaturas (prioridade, renumeração e validação) estão em triggers
do PostgreSQL, criados na migração 0002 desta app.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


class OrigemGrupo(models.TextChoices):
    CANDIDATURA = "CANDIDATURA", "Candidatura em grupo"
    JUNCAO = "JUNCAO", "Junção pelo docente"


class EstadoGrupo(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    ATIVO = "ATIVO", "Ativo"
    RECUSADO = "RECUSADO", "Recusado"
    DISSOLVIDO = "DISSOLVIDO", "Dissolvido"


class EstadoCandidatura(models.TextChoices):
    PENDENTE_CONFIRMACAO = "PENDENTE_CONFIRMACAO", "Pendente de confirmação"
    ATIVA = "ATIVA", "Ativa"
    RECUSADA = "RECUSADA", "Recusada"
    CONTEMPLADA = "CONTEMPLADA", "Contemplada"
    ENCERRADA = "ENCERRADA", "Encerrada"
    CANCELADA = "CANCELADA", "Cancelada"


class MotivoFim(models.TextChoices):
    SEM_CREDITOS = "SEM_CREDITOS", "Sem os créditos exigidos"
    TFC_ATRIBUIDO_A_OUTRO = "TFC_ATRIBUIDO_A_OUTRO", "TFC atribuído a outro candidato"
    ALUNO_CONTEMPLADO = "ALUNO_CONTEMPLADO", "Aluno já contemplado"
    RECUSADA_PELO_COLEGA = "RECUSADA_PELO_COLEGA", "Recusada pelo colega"
    SEM_CONFIRMACAO = "SEM_CONFIRMACAO", "Sem confirmação a tempo"
    DESISTENCIA = "DESISTENCIA", "Desistência"
    CANCELADA_PELO_ALUNO = "CANCELADA_PELO_ALUNO", "Cancelada pelo aluno"
    SUBSTITUIDA = "SUBSTITUIDA", "Substituída"


NA_LISTA = [EstadoCandidatura.PENDENTE_CONFIRMACAO, EstadoCandidatura.ATIVA]


class Grupo(models.Model):
    """Unidade que se candidata. Uma candidatura individual é um grupo só com o submissor (colega vazio).

    Decisão da Reunião 8 (18/11): todas as candidaturas pertencem a um grupo, para haver uma só forma de
    lista de prioridades e uma só forma de tratar as candidaturas no backend e no frontend.
    """

    ano_letivo = models.ForeignKey("configuracao.AnoLetivo", on_delete=models.PROTECT, related_name="grupos")
    submissor = models.ForeignKey("configuracao.Aluno", on_delete=models.PROTECT, related_name="grupos_submetidos",
                                  help_text="Aluno que cria e altera as candidaturas do grupo.")
    colega = models.ForeignKey("configuracao.Aluno", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="grupos_como_colega",
                               help_text="Vazio numa candidatura individual. O colega confirma cada candidatura.")
    origem = models.CharField(max_length=15, choices=OrigemGrupo.choices, default=OrigemGrupo.CANDIDATURA)
    estado = models.CharField(max_length=10, choices=EstadoGrupo.choices, default=EstadoGrupo.PENDENTE,
                              help_text="Um grupo individual fica ativo ao ser criado; um grupo de dois fica ativo "
                                        "quando o colega confirma a primeira candidatura.")
    proposto_por = models.ForeignKey("configuracao.Docente", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="juncoes_propostas", help_text="Docente que propôs a junção (P-03.8).")
    aceite_submissor = models.BooleanField(default=True)
    aceite_colega = models.BooleanField(default=False)
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(submissor=models.F("colega")), name="grupo_alunos_diferentes"),
            # Um só grupo individual por aluno e ano (os grupos de dois são verificados por trigger, R4)
            models.UniqueConstraint(fields=["ano_letivo", "submissor"],
                                    condition=Q(colega__isnull=True) & ~Q(estado="DISSOLVIDO"),
                                    name="grupo_individual_unico"),
        ]

    @property
    def individual(self):
        return self.colega_id is None

    def __str__(self):
        if self.colega_id is None:
            return self.submissor.numero
        return f"{self.submissor.numero} + {self.colega.numero}"


class Candidatura(models.Model):
    ano_letivo = models.ForeignKey("configuracao.AnoLetivo", on_delete=models.PROTECT, related_name="candidaturas")
    proposta = models.ForeignKey("propostas.Proposta", on_delete=models.PROTECT, related_name="candidaturas")
    grupo = models.ForeignKey(Grupo, on_delete=models.PROTECT, related_name="candidaturas",
                              help_text="Grupo que se candidata (só com o submissor, se for individual).")
    prioridade = models.PositiveSmallIntegerField(null=True, blank=True,
                                                  help_text="Só existe enquanto a candidatura está na lista.")
    estado = models.CharField(max_length=25, choices=EstadoCandidatura.choices, default=EstadoCandidatura.ATIVA)
    motivo_fim = models.CharField(max_length=25, choices=MotivoFim.choices, blank=True)
    substitui = models.OneToOneField("self", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="substituida_por")
    data_submissao = models.DateTimeField(auto_now_add=True)
    data_estado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["grupo", "prioridade"]
        constraints = [
            # R1: o grupo não se candidata duas vezes ao mesmo TFC (entre grupos diferentes, verifica o trigger R9)
            models.UniqueConstraint(fields=["proposta", "grupo"], condition=Q(estado__in=NA_LISTA),
                                    name="candidatura_unica_por_tfc"),
            # R2: sem prioridades repetidas na lista do grupo
            models.UniqueConstraint(fields=["grupo", "prioridade"], condition=Q(estado__in=NA_LISTA),
                                    name="prioridade_unica"),
        ]

    def __str__(self):
        return f"{self.grupo} → {self.proposta} ({self.get_estado_display()})"


class Selecao(models.Model):
    """Seleção do candidato de uma proposta (P-03.7).

    Decisão da Reunião 8 (18/11): o orientador ou o proponente seleciona o candidato e a coordenação confirma,
    o que publica a atribuição (função confirmar_selecao, que chama atribuir_tfc).
    """

    proposta = models.ForeignKey("propostas.Proposta", on_delete=models.CASCADE, related_name="selecoes")
    candidatura = models.OneToOneField(Candidatura, on_delete=models.CASCADE, related_name="selecao")
    posicao = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Posição na ordenação dos candidatos.")
    pontuacao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    selecionada = models.BooleanField(default=False)
    selecionada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name="+")
    data_selecao = models.DateTimeField(null=True, blank=True)
    justificacao_ajuste = models.TextField(blank=True)
    confirmada = models.BooleanField(default=False)
    confirmada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name="+")
    data_confirmacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "seleção"
        verbose_name_plural = "seleções"
        ordering = ["proposta", "posicao"]
        constraints = [
            # Só um candidato selecionado por proposta
            models.UniqueConstraint(fields=["proposta"], condition=Q(selecionada=True), name="um_selecionado_por_tfc"),
        ]
