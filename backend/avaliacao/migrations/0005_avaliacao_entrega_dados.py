"""Reunião 8 (18/11), 2.ª parte: as avaliações que já existem passam a apontar para a entrega do seu TFC e
momento (criada, se não existir)."""
from django.db import migrations


def ligar_a_entrega(apps, schema_editor):
    Avaliacao = apps.get_model("avaliacao", "Avaliacao")
    Entrega = apps.get_model("tfc", "Entrega")
    for a in Avaliacao.objects.filter(entrega__isnull=True):
        entrega, _ = Entrega.objects.get_or_create(tfc_id=a.tfc_id, momento_id=a.momento_id)
        Avaliacao.objects.filter(id=a.id).update(entrega=entrega)


class Migration(migrations.Migration):
    dependencies = [("avaliacao", "0004_avaliacao_entrega")]
    operations = [migrations.RunPython(ligar_a_entrega, migrations.RunPython.noop)]
