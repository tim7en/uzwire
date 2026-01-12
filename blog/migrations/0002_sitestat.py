from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("blog", "0001_initial"),
	]

	operations = [
		migrations.RunSQL(
			sql=(
				"DROP TABLE IF EXISTS blog_sitestat CASCADE;"
				"DROP SEQUENCE IF EXISTS blog_sitestat_id_seq CASCADE;"
			),
			reverse_sql=migrations.RunSQL.noop,
		),
		migrations.CreateModel(
			name="SiteStat",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
				("key", models.CharField(max_length=64, unique=True)),
				("value", models.BigIntegerField(default=0)),
				("updated_at", models.DateTimeField(auto_now=True)),
			],
			options={
				"verbose_name": "Site stat",
				"verbose_name_plural": "Site stats",
			},
		),
	]
