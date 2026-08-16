from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="currency",
            field=models.CharField(
                default="XAF",
                help_text="ISO 4217 currency snapshot for this invoice.",
                max_length=3,
            ),
        ),
    ]
