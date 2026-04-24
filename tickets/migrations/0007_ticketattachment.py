from django.db import migrations, models
import django.db.models.deletion
import tickets.models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0006_employee_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('ticket', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='tickets.ticket',
                )),
                ('file',        models.ImageField(upload_to=tickets.models.attachment_upload_path)),
                ('filename',    models.CharField(blank=True, max_length=255)),
                ('uploaded_by', models.CharField(blank=True, max_length=120)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Attachment',
                'verbose_name_plural': 'Attachments',
                'ordering': ['uploaded_at'],
            },
        ),
    ]