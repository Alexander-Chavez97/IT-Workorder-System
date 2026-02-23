from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_employee'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='submitter',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tickets',
                to='tickets.employee',
                verbose_name='Submitted By',
            ),
        ),
    ]
