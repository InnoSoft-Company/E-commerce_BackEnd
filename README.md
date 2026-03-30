# BLANKO Backend — Django REST API

## التشغيل السريع

### 1. تثبيت المتطلبات
```bash
cd blanko-backend
pip install -r requirements.txt
```

### 2. إعداد قاعدة البيانات وتشغيل الـ Server
```bash
bash setup.sh
```

هذا السكريبت يقوم بـ:
- تثبيت المتطلبات
- إنشاء قاعدة البيانات (SQLite)
- تشغيل الـ migrations
- ملء البيانات الأولية (admin + products + settings)
- تشغيل الـ server على port 8000

### بيانات الدخول
- **Admin**: admin@blanko.com / admin123
- **Django Admin Panel**: http://localhost:8000/django-admin/

---

## API Endpoints

### Auth
| Method | URL | الوظيفة |
|--------|-----|---------|
| POST | /api/auth/register/ | تسجيل حساب جديد |
| POST | /api/auth/login/ | تسجيل الدخول → JWT token |
| POST | /api/auth/logout/ | تسجيل الخروج |
| GET  | /api/auth/me/ | بيانات المستخدم الحالي |
| PUT  | /api/auth/me/update/ | تعديل البيانات الشخصية |
| POST | /api/auth/refresh/ | تجديد الـ access token |

### Products
| Method | URL | الوظيفة |
|--------|-----|---------|
| GET  | /api/products/ | قائمة المنتجات (مع فلتر) |
| GET  | /api/products/{id}/ | تفاصيل منتج |
| POST | /api/products/ | إضافة منتج (admin) |
| PATCH| /api/products/{id}/ | تعديل منتج (admin) |
| DELETE | /api/products/{id}/ | حذف منتج (admin) |

**Query params:** `?category=Women&sort=newest&featured=true&trending=true&min_price=50&max_price=200&search=shirt`

### Orders
| Method | URL | الوظيفة |
|--------|-----|---------|
| POST | /api/orders/ | إنشاء طلب جديد |
| GET  | /api/orders/ | طلباتي (مستخدم) أو كل الطلبات (admin) |
| PATCH| /api/orders/{id}/update_status/ | تغيير حالة الطلب (admin) |
| GET  | /api/orders/dashboard_stats/ | إحصائيات لوحة التحكم (admin) |

### Coupons
| Method | URL | الوظيفة |
|--------|-----|---------|
| POST | /api/coupons/validate/ | التحقق من كوبون |
| GET  | /api/coupons/ | قائمة الكوبونات (admin) |
| POST | /api/coupons/ | إضافة كوبون (admin) |
| PATCH| /api/coupons/{id}/ | تعديل كوبون (admin) |
| DELETE | /api/coupons/{id}/ | حذف كوبون (admin) |

### Wishlist (يتطلب تسجيل دخول)
| Method | URL | الوظيفة |
|--------|-----|---------|
| GET  | /api/wishlist/ | قائمة المفضلة |
| POST | /api/wishlist/add/ | إضافة للمفضلة |
| DELETE | /api/wishlist/remove/{product_id}/ | حذف من المفضلة |

### Admin Only
| Method | URL | الوظيفة |
|--------|-----|---------|
| GET | /api/admin/users/ | قائمة العملاء |
| GET | /api/admin/settings/ | إعدادات المتجر |
| POST | /api/admin/settings/update/ | حفظ الإعدادات |

---

## هيكل المشروع

```
blanko-backend/
├── blanko/              # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── api/                 # Main app
│   ├── models.py        # Database models
│   ├── serializers.py   # API serializers
│   ├── views.py         # API views
│   ├── urls.py          # URL routing
│   └── admin.py         # Django admin config
├── manage.py
├── seed_data.py         # Initial data script
├── requirements.txt
└── setup.sh             # One-command setup
```
