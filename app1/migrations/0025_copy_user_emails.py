from django.db import migrations

def copy_emails(apps, schema_editor):
    for model_name in ('Restaurant', 'NGO'):
        Model = apps.get_model('app1', model_name)
        for profile in Model.objects.select_related('user'):
            if profile.contact_email and not profile.user.email:
                profile.user.email = profile.contact_email
                profile.user.save(update_fields=['email'])


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0024_donation_food_condition_and_more'),
    ]

    operations = [
        migrations.RunPython(copy_emails, migrations.RunPython.noop),
    ]