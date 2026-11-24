"""Reunião 8 (18/11), 1.ª parte: preparar as candidaturas para pertencerem sempre a um grupo e acrescentar
a seleção pelo orientador ou proponente, com confirmação pela coordenação.

Retira as regras antigas da lista de candidaturas (são recriadas na migração 0008, já por grupo).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

DROP_REGRAS = r"""
DROP TRIGGER IF EXISTS candidatura_regressa_a_lista ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_historico ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_depois_de_sair ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_antes_de_sair ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_validar_nova ON candidaturas_candidatura;
DROP FUNCTION IF EXISTS candidatura_regressa_a_lista();
DROP FUNCTION IF EXISTS mover_candidatura(bigint, int);
DROP FUNCTION IF EXISTS candidatura_historico();
DROP FUNCTION IF EXISTS candidatura_depois_de_sair();
DROP FUNCTION IF EXISTS candidatura_antes_de_sair();
DROP FUNCTION IF EXISTS candidatura_validar_nova();
DROP FUNCTION IF EXISTS renumerar_lista(bigint, bigint, bigint);
DROP FUNCTION IF EXISTS atribuir_tfc(bigint, bigint, bigint);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("candidaturas", "0004_regressa_a_lista"),
        ("tfc", "0002_atribuir_tfc"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunSQL(DROP_REGRAS, migrations.RunSQL.noop),
        migrations.RemoveConstraint(model_name="candidatura", name="candidatura_unica_por_tfc"),
        migrations.RemoveConstraint(model_name="candidatura", name="prioridade_unica_individual"),
        migrations.RemoveConstraint(model_name="candidatura", name="prioridade_unica_grupo"),
        migrations.RemoveConstraint(model_name="grupo", name="grupo_ativo_unico_submissor"),
        migrations.RemoveConstraint(model_name="grupo", name="grupo_ativo_unico_colega"),
        migrations.AlterField(
            model_name="grupo", name="colega",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="grupos_como_colega", to="configuracao.aluno",
                                    help_text="Vazio numa candidatura individual. O colega confirma cada candidatura."),
        ),
        migrations.AlterField(
            model_name="grupo", name="submissor",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="grupos_submetidos",
                                    to="configuracao.aluno", help_text="Aluno que cria e altera as candidaturas do grupo."),
        ),
        migrations.AlterField(
            model_name="grupo", name="estado",
            field=models.CharField(choices=[("PENDENTE", "Pendente"), ("ATIVO", "Ativo"), ("RECUSADO", "Recusado"),
                                            ("DISSOLVIDO", "Dissolvido")], default="PENDENTE", max_length=10,
                                   help_text="Um grupo individual fica ativo ao ser criado; um grupo de dois fica ativo "
                                             "quando o colega confirma a primeira candidatura."),
        ),
        # Seleção e confirmação
        migrations.AlterField(
            model_name="selecao", name="posicao",
            field=models.PositiveSmallIntegerField(blank=True, null=True, help_text="Posição na ordenação dos candidatos."),
        ),
        migrations.AddField(model_name="selecao", name="selecionada", field=models.BooleanField(default=False)),
        migrations.AddField(
            model_name="selecao", name="selecionada_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="+", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(model_name="selecao", name="data_selecao", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="selecao", name="data_confirmacao",
                            field=models.DateTimeField(blank=True, null=True)),
        migrations.AddConstraint(
            model_name="selecao",
            constraint=models.UniqueConstraint(condition=models.Q(("selecionada", True)), fields=("proposta",),
                                               name="um_selecionado_por_tfc"),
        ),
    ]
