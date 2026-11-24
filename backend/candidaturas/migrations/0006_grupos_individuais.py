"""Reunião 8 (18/11), 2.ª parte: cada candidatura individual que já existe passa a pertencer a um grupo
só com esse aluno."""
from django.db import migrations


def criar_grupos_individuais(apps, schema_editor):
    Candidatura = apps.get_model("candidaturas", "Candidatura")
    Grupo = apps.get_model("candidaturas", "Grupo")
    for c in Candidatura.objects.filter(grupo__isnull=True):
        grupo = (Grupo.objects.filter(ano_letivo_id=c.ano_letivo_id, submissor_id=c.aluno_id, colega__isnull=True)
                 .exclude(estado="DISSOLVIDO").first())
        if grupo is None:
            grupo = Grupo.objects.create(ano_letivo_id=c.ano_letivo_id, submissor_id=c.aluno_id, colega=None,
                                         estado="ATIVO", aceite_colega=True)
        Candidatura.objects.filter(id=c.id).update(grupo=grupo)


class Migration(migrations.Migration):
    dependencies = [("candidaturas", "0005_grupos_e_selecao")]
    operations = [migrations.RunPython(criar_grupos_individuais, migrations.RunPython.noop)]
