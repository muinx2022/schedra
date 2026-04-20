from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('back_office', '0004_socialprovidersettings_linkedin_client_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='socialprovidersettings',
            name='pinterest_app_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='socialprovidersettings',
            name='pinterest_app_secret_enc',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='socialprovidersettings',
            name='pinterest_scopes',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
