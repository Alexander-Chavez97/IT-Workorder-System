from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0002_ticket_issue_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=30, unique=True,
                                                 verbose_name='Employee ID')),
                ('first_name',  models.CharField(max_length=60, verbose_name='First Name')),
                ('last_name',   models.CharField(max_length=60, verbose_name='Last Name')),
                ('email',       models.EmailField(max_length=254, unique=True,
                                                  verbose_name='Email')),
                ('department',  models.CharField(max_length=80, verbose_name='Department',
                    choices=[
                        ('Police Department', 'Police Department'),
                        ('Fire Department', 'Fire Department'),
                        ('Utilities', 'Utilities'),
                        ("City Manager's Office", "City Manager's Office"),
                        ('Health Department', 'Health Department'),
                        ('Finance', 'Finance'),
                        ('Public Works', 'Public Works'),
                        ('Parks & Recreation', 'Parks & Recreation'),
                        ('City Clerk', 'City Clerk'),
                        ('Planning & Zoning', 'Planning & Zoning'),
                    ]
                )),
                ('password',   models.CharField(max_length=256, verbose_name='Password Hash')),
                ('is_active',  models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Employee',
                'verbose_name_plural': 'Employees',
                'ordering': ['last_name', 'first_name'],
            },
        ),
    ]
