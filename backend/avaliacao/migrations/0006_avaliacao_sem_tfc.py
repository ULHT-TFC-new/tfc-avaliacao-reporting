"""Reunião 8 (18/11), 3.ª parte: a avaliação deixa de apontar diretamente para o TFC e o momento."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("avaliacao", "0005_avaliacao_entrega_dados")]
    operations = [
        migrations.RemoveField(model_name="avaliacao", name="tfc"),
        migrations.RemoveField(model_name="avaliacao", name="momento"),
        migrations.AlterField(
            model_name="avaliacao", name="entrega",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="avaliacoes",
                                    to="tfc.entrega"),
        ),
        migrations.AddConstraint(
            model_name="avaliacao",
            constraint=models.UniqueConstraint(fields=("entrega", "jurado"), name="avaliacao_unica_por_jurado"),
        ),
    ]
