from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hospital", "0002_externalhospital_servicedefinition_specialty_and_more")]

    operations = [
        migrations.AddField(
            model_name="hospitalprofile",
            name="billing_currency",
            field=models.CharField(
                default="XAF",
                help_text="ISO 4217 currency code used for new financial records.",
                max_length=3,
            ),
        ),
    ]
