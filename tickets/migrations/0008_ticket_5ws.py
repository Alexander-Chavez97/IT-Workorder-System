from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_ticketattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='affected_users',
            field=models.TextField(
                blank=True,
                verbose_name='Who Else Is Affected',
                help_text='List other employees, teams, or systems impacted.',
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='when_started',
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name='When Did This Start',
                help_text="e.g. 'This morning around 9am', 'Since last Friday'",
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='business_impact',
            field=models.TextField(
                blank=True,
                verbose_name='Business Impact / Why It Matters',
                help_text='Describe what work is blocked, who is waiting, any deadlines affected.',
            ),
        ),
    ]