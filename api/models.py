from django.db import models
from django.contrib.auth.models import AbstractUser


# ── Custom User ─────────────────────────────────
class User(AbstractUser):
    phone    = models.CharField(max_length=20, blank=True)
    address  = models.TextField(blank=True)
    city     = models.CharField(max_length=100, blank=True)
    country  = models.CharField(max_length=100, blank=True, default="مصر")
    is_admin = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username


# ── Category ─────────────────────────────────────
class Category(models.Model):
    name    = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True)
    slug    = models.SlugField(unique=True)
    image   = models.ImageField(upload_to="categories/", null=True, blank=True)
    count   = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


# ── Product ───────────────────────────────────────
class Product(models.Model):
    name        = models.CharField(max_length=200)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    image       = models.URLField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True)
    rating      = models.FloatField(default=0.0)
    reviews     = models.PositiveIntegerField(default=0)
    in_stock    = models.BooleanField(default=True)
    featured    = models.BooleanField(default=False)
    trending    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def has_variants(self):
        """True if this product uses the new variant system."""
        return self.variants.exists()

    @property
    def is_available(self):
        """
        A product is available if:
        - It has no variants -> fall back to legacy in_stock field
        - It has variants -> at least one variant has stock > 0
        """
        if self.has_variants:
            return self.variants.filter(stock__gt=0).exists()
        return self.in_stock

    def sync_in_stock(self):
        """Keep the legacy in_stock field in sync with variant availability."""
        if self.has_variants:
            self.in_stock = self.variants.filter(stock__gt=0).exists()
            Product.objects.filter(pk=self.pk).update(in_stock=self.in_stock)


# ── ProductVariant (Color) ─────────────────────────
# Represents one COLOR of a product. Each color has its own image
# and multiple sizes, each size with its own stock quantity.
class ProductVariant(models.Model):
    product   = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color     = models.CharField(max_length=100, verbose_name="اللون")
    color_hex = models.CharField(
        max_length=7, blank=True, default="",
        help_text="كود اللون hex مثل #FF0000 (اختياري)",
        verbose_name="كود اللون"
    )
    image     = models.CharField(max_length=500, blank=True, default="", verbose_name="صورة اللون")
    # Total stock across all sizes — computed & stored for quick filtering
    stock     = models.PositiveIntegerField(default=0, verbose_name="المخزون الكلي")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together     = ("product", "color")
        verbose_name        = "متغير المنتج (لون)"
        verbose_name_plural = "متغيرات المنتج (ألوان)"
        ordering            = ["color"]

    def __str__(self):
        return f"{self.product.name} — {self.color}"

    def recalculate_stock(self):
        """Sum up all size quantities and save total stock."""
        from django.db.models import Sum
        total = self.sizes.aggregate(total=Sum("quantity"))["total"] or 0
        self.stock = total
        ProductVariant.objects.filter(pk=self.pk).update(stock=total)
        # Keep parent product in_stock in sync
        self.product.sync_in_stock()


# ── ProductSize ───────────────────────────────────
# Represents one SIZE inside a color variant. Each has its own quantity.
class ProductSize(models.Model):
    variant  = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="sizes")
    size     = models.CharField(max_length=50, verbose_name="المقاس")
    quantity = models.PositiveIntegerField(default=0, verbose_name="الكمية")

    class Meta:
        unique_together     = ("variant", "size")
        verbose_name        = "مقاس"
        verbose_name_plural = "مقاسات"
        ordering            = ["size"]

    def __str__(self):
        return f"{self.variant} / {self.size} ({self.quantity})"

    def reduce_stock(self, qty: int):
        """
        Decrease quantity by qty. Raises ValueError if not enough stock.
        After reducing, recalculates the parent variant's total stock.
        """
        if self.quantity < qty:
            raise ValueError(
                f"الكمية المطلوبة ({qty}) أكبر من المتاح ({self.quantity}) "
                f"للمقاس {self.size} اللون {self.variant.color}"
            )
        self.quantity -= qty
        ProductSize.objects.filter(pk=self.pk).update(quantity=self.quantity)
        self.variant.recalculate_stock()


# ── Coupon ────────────────────────────────────────
class Coupon(models.Model):
    DISCOUNT_TYPES = [("percent", "نسبة مئوية"), ("fixed", "مبلغ ثابت")]

    code          = models.CharField(max_length=50, unique=True)
    discount      = models.DecimalField(max_digits=6, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="percent")
    uses          = models.PositiveIntegerField(default=0)
    max_uses      = models.PositiveIntegerField(default=100)
    active        = models.BooleanField(default=True)
    expiry        = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


# ── ShippingZone ──────────────────────────────────
class ShippingZone(models.Model):
    governorate = models.CharField(max_length=100, unique=True, verbose_name="المحافظة")
    fee         = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="سعر الشحن")
    enabled     = models.BooleanField(default=True, verbose_name="متاح")
    order       = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        ordering = ["order", "governorate"]
        verbose_name        = "منطقة شحن"
        verbose_name_plural = "مناطق الشحن"

    def __str__(self):
        return f"{self.governorate} — {self.fee} ج.م"


# ── Order ─────────────────────────────────────────
class Order(models.Model):
    STATUS_CHOICES = [
        ("processing", "قيد المعالجة"),
        ("shipping",   "في الطريق"),
        ("delivered",  "تم التسليم"),
        ("cancelled",  "ملغي"),
    ]
    PAYMENT_CHOICES = [
        ("deposit",  "الدفع عند الاستلام"),
        ("vodafone", "Vodafone Cash"),
        ("instapay", "InstaPay"),
        ("bank",     "تحويل بنكي"),
        ("card",     "بطاقة بنكية"),
        ("paybump",  "PayBump — دفع مباشر"),
    ]

    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    email          = models.EmailField(blank=True, default="")
    phone          = models.CharField(max_length=20)
    address        = models.TextField(blank=True, default="")
    city           = models.CharField(max_length=100)
    zip_code       = models.CharField(max_length=20, blank=True)
    subtotal       = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee   = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tax            = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total          = models.DecimalField(max_digits=10, decimal_places=2)
    coupon         = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount= models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="deposit")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.pk:04d} — {self.first_name} {self.last_name}"


class OrderItem(models.Model):
    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product  = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name     = models.CharField(max_length=200)
    price    = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    size     = models.CharField(max_length=20, blank=True)
    color    = models.CharField(max_length=50, blank=True)
    image    = models.URLField(max_length=500, blank=True)

    @property
    def line_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.name} x{self.quantity}"


# ── Cart Items ────────────────────────────────────
class CartItem(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size     = models.CharField(max_length=50, blank=True)
    color    = models.CharField(max_length=50, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "product", "size", "color")
        verbose_name = "عنصر السلة"
        verbose_name_plural = "عناصر السلة"

    @property
    def line_total(self):
        return float(self.product.price) * self.quantity

    def __str__(self):
        return f"{self.user.username} → {self.product.name} x{self.quantity}"


# ── Wishlist ──────────────────────────────────────
class WishlistItem(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        verbose_name = "عنصر قائمة الرغبات"
        verbose_name_plural = "قائمة الرغبات"

    def __str__(self):
        return f"{self.user.username} → {self.product.name}"


# ── Store Settings ────────────────────────────────
class StoreSetting(models.Model):
    key   = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)

    def __str__(self):
        return self.key
