# Generated manually — adds ProductVariant and ProductSize models

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_alter_wishlistitem_options_cartitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('color', models.CharField(max_length=100, verbose_name='اللون')),
                ('color_hex', models.CharField(
                    blank=True, default='', max_length=7,
                    help_text='كود اللون hex مثل #FF0000 (اختياري)',
                    verbose_name='كود اللون'
                )),
                ('image', models.CharField(blank=True, default='', max_length=500, verbose_name='صورة اللون')),
                ('stock', models.PositiveIntegerField(default=0, verbose_name='المخزون الكلي')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='variants',
                    to='api.product'
                )),
            ],
            options={
                'verbose_name': 'متغير المنتج (لون)',
                'verbose_name_plural': 'متغيرات المنتج (ألوان)',
                'ordering': ['color'],
                'unique_together': {('product', 'color')},
            },
        ),
        migrations.CreateModel(
            name='ProductSize',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.CharField(max_length=50, verbose_name='المقاس')),
                ('quantity', models.PositiveIntegerField(default=0, verbose_name='الكمية')),
                ('variant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sizes',
                    to='api.productvariant'
                )),
            ],
            options={
                'verbose_name': 'مقاس',
                'verbose_name_plural': 'مقاسات',
                'ordering': ['size'],
                'unique_together': {('variant', 'size')},
            },
        ),
    ]
