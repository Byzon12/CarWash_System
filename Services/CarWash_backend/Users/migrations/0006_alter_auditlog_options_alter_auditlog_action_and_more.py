# Generated by Django 5.2.1 on 2025-06-05 09:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0005_auditlog'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='auditlog',
            options={'ordering': ['-timestamp'], 'verbose_name': 'Audit Log', 'verbose_name_plural': 'Audit Logs'},
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('register', 'register user'), ('login', 'login user'), ('logout', 'logout user'), ('login_failed', 'login failed'), ('update_profile', 'update profile'), ('delete_account', 'delete account'), ('reset_password', 'reset password'), ('change_password', 'change password'), ('other', 'other')], max_length=50),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='success',
            field=models.BooleanField(default=False),
        ),
    ]
