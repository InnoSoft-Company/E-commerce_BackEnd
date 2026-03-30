from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Category

def update_category_count(product):
    if product.category:
        product.category.count = product.category.products.count()
        product.category.save(update_fields=["count"])

@receiver(post_save, sender=Product)
def product_saved(sender, instance, **kwargs):
    update_category_count(instance)

@receiver(post_delete, sender=Product)
def product_deleted(sender, instance, **kwargs):
    update_category_count(instance)
