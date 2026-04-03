from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_ticket_submitter'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('ticket', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='history',
                    to='tickets.ticket',
                )),
                ('action', models.CharField(
                    max_length=20,
                    choices=[
                        ('Created',   'Created'),
                        ('Escalated', 'Escalated'),
                        ('Resolved',  'Resolved'),
                        ('Reopened',  'Reopened'),
                        ('Note',      'Note Added'),
                        ('Assigned',  'Reassigned'),
                    ],
                )),
                ('note',           models.TextField(blank=True, verbose_name='Note')),
                ('changed_by',     models.CharField(blank=True, max_length=120,
                                                    verbose_name='Changed By')),
                ('priority_before', models.IntegerField(blank=True, null=True)),
                ('priority_after',  models.IntegerField(blank=True, null=True)),
                ('team_before',    models.CharField(blank=True, max_length=100)),
                ('team_after',     models.CharField(blank=True, max_length=100)),
                ('timestamp',      models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Ticket History Entry',
                'verbose_name_plural': 'Ticket History',
                'ordering': ['timestamp'],
            },
        ),
    ]