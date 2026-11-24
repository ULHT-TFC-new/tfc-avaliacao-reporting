"""Reunião 8 (18/11), 1.ª parte: a avaliação passa a avaliar a entrega (que identifica o TFC e o momento)."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("avaliacao", "0003_modelo_2026_27"), ("tfc", "0003_atribuir_e_confirmar")]
    operations = [
        migrations.RemoveConstraint(model_name="avaliacao", name="avaliacao_unica_por_jurado"),
        migrations.AddField(
            model_name="avaliacao", name="entrega",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="avaliacoes", to="tfc.entrega"),
        ),
    ]
