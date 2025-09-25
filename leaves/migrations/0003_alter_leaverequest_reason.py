from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leaverequest',
            name='reason',
            field=models.TextField(blank=True, null=True, help_text='Optional reason provided by employee'),
        ),
    ]
