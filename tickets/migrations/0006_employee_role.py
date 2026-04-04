from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0005_tickethistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='role',
            field=models.CharField(
                choices=[
                    ('dept',  'Department Employee'),
                    ('ist',   'IST Staff'),
                    ('admin', 'IST Admin'),
                ],
                default='dept',
                max_length=10,
                verbose_name='Role',
            ),
        ),
    ]