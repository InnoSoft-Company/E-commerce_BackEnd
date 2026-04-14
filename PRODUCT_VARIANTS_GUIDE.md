# 📦 Product Variants System — دليل العمل

## المفهوم الأساسي

```
Product (منتج)
  ├─ ProductVariant (لون واحد)
  │   ├─ image: صورة خاصة باللون
  │   └─ ProductSize × N (مقاسات متعددة)
  │       └─ quantity: كمية لكل مقاس
  │
  └─ ProductVariant (لون آخر)
      ├─ image: صورة خاصة باللون
      └─ ProductSize × N (مقاسات متعددة)
          └─ quantity: كمية لكل مقاس
```

## مثال عملي

**المنتج:** T-Shirt

**الألوان المتاحة:**
- 🟫 **أسود** (أسود) — صورة: `black.jpg`
  - مقاسات:
    - S: 5 وحدات
    - M: 10 وحدات
    - L: 0 وحدات (انتهى)

- ⚪ **أبيض** (White) — صورة: `white.jpg`
  - مقاسات:
    - S: 3 وحدات
    - M: 8 وحدات

---

## API Endpoints

### 1️⃣ إضافة منتج جديد مع الألوان

**Endpoint:** `POST /api/products/`

**Content-Type:** `application/json`

```json
{
  "name": "T-Shirt",
  "price": "29.99",
  "category": 5,
  "category": "Clothing",  // أو الـ ID
  "image": "http://example.com/main.jpg",
  "description": "منتج عالي الجودة",
  "featured": true,
  "variants": [
    {
      "color": "أسود",
      "color_hex": "#000000",
      "image": "http://example.com/black.jpg",
      "sizes": [
        {"size": "S", "quantity": 5},
        {"size": "M", "quantity": 10},
        {"size": "L", "quantity": 0}
      ]
    },
    {
      "color": "أبيض",
      "color_hex": "#FFFFFF",
      "image": "http://example.com/white.jpg",
      "sizes": [
        {"size": "S", "quantity": 3},
        {"size": "M", "quantity": 8}
      ]
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "name": "T-Shirt",
  "price": "29.99",
  "category": 5,
  "category_name": "Clothing",
  "image": "http://localhost:8000/media/products/main.jpg",
  "description": "منتج عالي الجودة",
  "variants": [
    {
      "id": 1,
      "color": "أسود",
      "color_hex": "#000000",
      "image": "http://localhost:8000/media/products/black.jpg",
      "total_stock": 15,
      "sizes": [
        {"id": 1, "size": "S", "quantity": 5},
        {"id": 2, "size": "M", "quantity": 10}
      ]
    }
  ],
  "is_available": true,
  "rating": 0.0,
  "reviews": 0
}
```

---

### 2️⃣ عرض جميع الألوان والأحجام لمنتج

**Endpoint:** `GET /api/products/{id}/variants/`

**Response:**
```json
[
  {
    "id": 1,
    "color": "أسود",
    "color_hex": "#000000",
    "image": "http://localhost:8000/media/products/black.jpg",
    "total_stock": 15,
    "sizes": [
      {"id": 1, "size": "S", "quantity": 5},
      {"id": 2, "size": "M", "quantity": 10}
    ]
  },
  {
    "id": 2,
    "color": "أبيض",
    "color_hex": "#FFFFFF",
    "image": "http://localhost:8000/media/products/white.jpg",
    "total_stock": 11,
    "sizes": [
      {"id": 3, "size": "S", "quantity": 3},
      {"id": 4, "size": "M", "quantity": 8}
    ]
  }
]
```

---

### 3️⃣ عرض المخزون المفصل (للتجار)

**Endpoint:** `GET /api/products/{id}/stock/`

**الفائدة:** معرفة الكميات بالضبط لكل لون وكل مقاس

**Response:**
```json
{
  "product_id": 1,
  "product_name": "T-Shirt",
  "is_available": true,
  "colors": [
    {
      "color": "أسود",
      "color_hex": "#000000",
      "image": "http://localhost:8000/media/products/black.jpg",
      "stock": 15,
      "sizes": [
        {"size": "S", "quantity": 5},
        {"size": "M", "quantity": 10},
        {"size": "L", "quantity": 0}
      ]
    }
  ]
}
```

---

### 4️⃣ تعديل الألوان والأحجام (إضافة لون جديد أو تحديث الكميات)

**Endpoint:** `POST /api/products/{id}/variants/update/`

**الملاحظات:**
- هذا الـ endpoint يستبدل جميع الألوان بـ الجديدة
- يمكنك إضافة ألوان جديدة أو إزالة القديمة ببساطة بعدم تضمينها

**Request:**
```json
{
  "variants": [
    {
      "color": "أسود",
      "color_hex": "#000000",
      "image": "http://example.com/black.jpg",
      "sizes": [
        {"size": "S", "quantity": 3},
        {"size": "M", "quantity": 7},
        {"size": "XL", "quantity": 2}
      ]
    },
    {
      "color": "أحمر",
      "color_hex": "#FF0000",
      "image": "http://example.com/red.jpg",
      "sizes": [
        {"size": "S", "quantity": 5},
        {"size": "M", "quantity": 6}
      ]
    }
  ]
}
```

---

## الخصائص المحسوبة تلقائياً

### 1. `ProductVariant.stock` — إجمالي مخزون اللون
```python
stock = مجموع جميع الـ quantities في الأحجام
```

يُحسب تلقائياً عند:
- إضافة/تعديل حجم
- تقليل المخزون عند شراء

### 2. `Product.is_available` — توفر المنتج
```python
is_available = يوجد على الأقل لون واحد بـ stock > 0
```

### 3. `Product.in_stock` — الحقل الموروث (للتوافقية العكسية)
يُحدَّث تلقائياً ليعكس حالة `is_available`

---

## الحقول القديمة المحذوفة

تم حذف الحقول التالية من `Product` model لأنها لم تعد مستخدمة:
- ❌ `sizes` (JSON Array)
- ❌ `colors` (JSON Array)
- ❌ `images` (JSON Array)

**السبب:** النظام الجديد (Variants) يوفر طريقة أفضل وأكثر مرونة:
- كل لون له صورة خاصة
- كل لون له عدة أحجام مع كميات منفصلة
- تتبع أفضل للمخزون

---

## مثال: سير العمل الكامل

### الخطوة 1: إنشاء منتج بسيط (بدون ألوان في البداية)
```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "T-Shirt",
    "price": "29.99",
    "category": "Clothing",
    "image": "http://example.com/main.jpg",
    "variants": []
  }'
```

### الخطوة 2: إضافة الألوان والأحجام
```bash
curl -X POST http://localhost:8000/api/products/1/variants/update/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "variants": [
      {
        "color": "أسود",
        "color_hex": "#000000",
        "image": "http://example.com/black.jpg",
        "sizes": [
          {"size": "S", "quantity": 10},
          {"size": "M", "quantity": 15}
        ]
      }
    ]
  }'
```

### الخطوة 3: عرض الألوان للعميل
```bash
curl http://localhost:8000/api/products/1/variants/
```

---

## ملاحظات تقنية مهمة

### حول الكميات الصفرية (quantity = 0)
- ❌ لا تُعرَض للعملاء العاديين
- ✅ تُعرَض للمديرين (للتتبع)

### حول `in_stock` الموروث
- لا تحتاج لتحديثه يدويًا — يُحدَّث تلقائياً
- استخدمه فقط للمنتجات القديمة التي لا تملك variants

### الفرز والتصفية
- المنتجات **بدون** variants متاحة: تستخدم حقل `in_stock` القديم
- المنتجات **مع** variants متاحة: يجب أن يكون لديها variant واحد على الأقل بـ stock > 0

---

## الأخطاء الشائعة

### ❌ خطأ: لون فارغ
```json
{
  "color": "",  // لا يُقبل — سيُتجاهل
  "sizes": []
}
```

### ✅ الحل:
```json
{
  "color": "أسود",  // يجب ملء اللون
  "color_hex": "#000000",
  "sizes": []
}
```

---

### ❌ خطأ: في FormData (عند رفع صور)
```
name: T-Shirt
price: 29.99
category: Clothing
image: <file>
variants: "not a valid JSON string"
```

### ✅ الحل:
```
name: T-Shirt
price: 29.99
category: Clothing
image: <file>
variants: "[{\"color\": \"أسود\", \"color_hex\": \"#000000\", \"sizes\": []}]"
```

---

## معلومات إضافية

**Migration:** تم حذف حقول legacy في `0008_remove_product_colors_remove_product_images_and_more.py`

**التاريخ:** تم التحديث في أبريل 2026
