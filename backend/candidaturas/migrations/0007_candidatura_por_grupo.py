"""Reunião 8 (18/11), 3.ª parte: a candidatura deixa de ter o aluno e passa a ter sempre um grupo."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("candidaturas", "0006_grupos_individuais")]

    operations = [
        migrations.RemoveField(model_name="candidatura", name="aluno"),
        migrations.AlterField(
            model_name="candidatura", name="grupo",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="candidaturas",
                                    to="candidaturas.grupo",
                                    help_text="Grupo que se candidata (só com o submissor, se for individual)."),
        ),
        migrations.AlterModelOptions(name="candidatura", options={"ordering": ["grupo", "prioridade"]}),
        migrations.AddConstraint(
            model_name="candidatura",
            constraint=models.UniqueConstraint(
                condition=models.Q(("estado__in", ["PENDENTE_CONFIRMACAO", "ATIVA"])),
                fields=("proposta", "grupo"), name="candidatura_unica_por_tfc"),
        ),
        migrations.AddConstraint(
            model_name="candidatura",
            constraint=models.UniqueConstraint(
                condition=models.Q(("estado__in", ["PENDENTE_CONFIRMACAO", "ATIVA"])),
                fields=("grupo", "prioridade"), name="prioridade_unica"),
        ),
        migrations.AddConstraint(
            model_name="grupo",
            constraint=models.UniqueConstraint(
                condition=models.Q(("colega__isnull", True), models.Q(("estado", "DISSOLVIDO"), _negated=True)),
                fields=("ano_letivo", "submissor"), name="grupo_individual_unico"),
        ),
    ]
