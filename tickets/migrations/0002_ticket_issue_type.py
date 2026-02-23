from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='issue_type',
            field=models.CharField(
                blank=True,
                max_length=40,
                verbose_name='Issue Type',
                default='',
            ),
            preserve_default=False,
        ),
    ]
