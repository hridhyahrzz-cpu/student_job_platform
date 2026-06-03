# Generated migration to fix applicant field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users_app', '0001_initial'),
        ('jobs_app', '0003_alter_applicationmodel_applicant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationmodel',
            name='applicant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users_app.usermodel'),
        ),
    ]
