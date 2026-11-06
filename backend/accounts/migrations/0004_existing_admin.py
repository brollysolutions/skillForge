from django.db import migrations


def promote_single_superuser(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    users = User.objects.using(schema_editor.connection.alias)
    if not users.filter(role='admin').exists():
        candidates = users.filter(is_superuser=True, role='trainer')
        if candidates.count() == 1:
            candidates.update(role='admin')


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_user_single_platform_admin')]
    operations = [migrations.RunPython(promote_single_superuser, migrations.RunPython.noop)]
