"""
تشغيل: python manage.py shell < seed_data.py
أو:    python seed_data.py  (بعد إعداد Django)
يملأ قاعدة البيانات بـ: Admin user + Categories + Products + Settings
"""
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blanko.settings")
django.setup()

from api.models import User, Category, Product, StoreSetting

print("🌱 Seeding database...")

# ── 1. Admin user ────────────────────────────────
if not User.objects.filter(username="admin").exists():
    admin = User.objects.create_superuser(
        username  = "admin",
        email     = "admin@blanko.com",
        password  = "admin123",
        first_name= "المدير",
        is_admin  = True,
    )
    print("✓ Admin created: admin@blanko.com / admin123")
else:
    print("✓ Admin already exists")

# ── 2. Categories ─────────────────────────────────
cats_data = [
    {"name": "Women",       "name_ar": "نساء",       "slug": "women"},
    {"name": "Men",         "name_ar": "رجال",       "slug": "men"},
    {"name": "Kids",        "name_ar": "أطفال",      "slug": "kids"},
    {"name": "Accessories", "name_ar": "إكسسوارات",  "slug": "accessories"},
]
cats = {}
for c in cats_data:
    obj, _ = Category.objects.get_or_create(slug=c["slug"], defaults={
        "name": c["name"], "name_ar": c["name_ar"],
    })
    cats[c["name"]] = obj
print(f"✓ {len(cats)} categories created")

# ── 3. Products ───────────────────────────────────
products_data = [
    {
        "name": "Classic White Shirt", "price": 89.99, "category": "Women",
        "image": "https://images.unsplash.com/photo-1669059921524-327a4c52cff3?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1669059921524-327a4c52cff3?w=600&q=80","https://images.unsplash.com/photo-1720005398225-4ea01c9d2b8f?w=600&q=80"],
        "description": "Elegant classic white shirt made from premium cotton.",
        "sizes": ["XS","S","M","L","XL"], "colors": ["White","Black","Beige"],
        "rating": 4.8, "reviews": 124, "in_stock": True, "featured": True, "trending": True,
    },
    {
        "name": "Elegant Summer Dress", "price": 149.99, "category": "Women",
        "image": "https://images.unsplash.com/photo-1720005398225-4ea01c9d2b8f?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1720005398225-4ea01c9d2b8f?w=600&q=80"],
        "description": "Beautiful flowing summer dress perfect for warm weather.",
        "sizes": ["XS","S","M","L","XL"], "colors": ["Pink","Blue","White"],
        "rating": 4.9, "reviews": 98, "in_stock": True, "featured": True, "trending": False,
    },
    {
        "name": "Men's Casual Jacket", "price": 199.99, "category": "Men",
        "image": "https://images.unsplash.com/photo-1490578474895-699cd4e2cf59?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1490578474895-699cd4e2cf59?w=600&q=80"],
        "description": "Versatile casual jacket perfect for any occasion.",
        "sizes": ["S","M","L","XL","XXL"], "colors": ["Navy","Black","Brown"],
        "rating": 4.7, "reviews": 87, "in_stock": True, "featured": True, "trending": True,
    },
    {
        "name": "Kids Colorful Set", "price": 59.99, "category": "Kids",
        "image": "https://images.unsplash.com/photo-1471286174890-9c112ffca5b4?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1471286174890-9c112ffca5b4?w=600&q=80"],
        "description": "Fun and colorful clothing set for kids.",
        "sizes": ["2Y","4Y","6Y","8Y","10Y"], "colors": ["Pink","Blue","Green","Red"],
        "rating": 4.6, "reviews": 63, "in_stock": True, "featured": False, "trending": True,
    },
    {
        "name": "Leather Handbag", "price": 249.99, "category": "Accessories",
        "image": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&q=80"],
        "description": "Premium leather handbag with elegant design.",
        "sizes": ["Free"], "colors": ["Black","Brown","Beige"],
        "rating": 4.9, "reviews": 156, "in_stock": True, "featured": True, "trending": True,
    },
    {
        "name": "Silk Evening Blouse", "price": 129.99, "category": "Women",
        "image": "https://images.unsplash.com/photo-1602303894456-398ce544d90b?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1602303894456-398ce544d90b?w=600&q=80"],
        "description": "Elegant silk blouse for special occasions.",
        "sizes": ["XS","S","M","L"], "colors": ["Black","White","Navy"],
        "rating": 4.8, "reviews": 79, "in_stock": True, "featured": True, "trending": False,
    },
    {
        "name": "Men's Oxford Shirt", "price": 119.99, "category": "Men",
        "image": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=600&q=80"],
        "description": "Classic oxford shirt for the modern gentleman.",
        "sizes": ["S","M","L","XL","XXL"], "colors": ["White","Blue","Gray"],
        "rating": 4.7, "reviews": 112, "in_stock": True, "featured": False, "trending": True,
    },
    {
        "name": "Silk Scarf", "price": 79.99, "category": "Accessories",
        "image": "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=600&q=80",
        "images": ["https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=600&q=80"],
        "description": "Luxurious silk scarf with elegant patterns.",
        "sizes": ["Free"], "colors": ["Pink","Blue","Beige","Red"],
        "rating": 4.9, "reviews": 45, "in_stock": True, "featured": False, "trending": True,
    },
]

for p in products_data:
    cat_name = p.pop("category")
    if not Product.objects.filter(name=p["name"]).exists():
        Product.objects.create(category=cats[cat_name], **p)
print(f"✓ {len(products_data)} products seeded")

# Update category counts
for cat in Category.objects.all():
    cat.count = cat.products.count()
    cat.save()

# ── 4. Store Settings ─────────────────────────────
defaults = {
    "store_name":       "Blanko Fashion House",
    "store_email":      "info@blanko.com",
    "store_phone":      "+20 100 000 0000",
    "store_address":    "القاهرة، مصر",
    "wa_number":        "201000000000",
    "free_shipping_min":"100",
    "shipping_fee":     "10",
    "tax_rate":         "10",
    "vodafone_num":     "010XXXXXXXX",
    "instapay_id":      "blanko@instapay",
    "bank_account":     "1234567890123456",
    "bank_name":        "بنك مصر",
}
for k, v in defaults.items():
    StoreSetting.objects.get_or_create(key=k, defaults={"value": v})
print(f"✓ {len(defaults)} store settings created")

print("\n✅ Seeding complete!")
print("=" * 40)
print("Admin login: admin@blanko.com / admin123")
print("API base:    http://localhost:8000/api/")
print("Django admin: http://localhost:8000/django-admin/")
