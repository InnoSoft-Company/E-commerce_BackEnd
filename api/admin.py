from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Category, Product, ProductVariant, ProductSize,
    Coupon, ShippingZone, Order, OrderItem, CartItem, WishlistItem, StoreSetting
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_admin", "is_staff"]
    fieldsets    = BaseUserAdmin.fieldsets + (
        ("Extra", {"fields": ("phone", "address", "city", "country", "is_admin")}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ["name", "name_ar", "slug", "count"]
    prepopulated_fields = {"slug": ("name",)}


# ── Product Variants (inline inside Product) ──────────────────────────────

class ProductSizeInline(admin.TabularInline):
    model  = ProductSize
    extra  = 3
    fields = ["size", "quantity"]


class ProductVariantInline(admin.StackedInline):
    model          = ProductVariant
    extra          = 1
    fields         = ["color", "color_hex", "image", "stock"]
    readonly_fields = ["stock"]
    show_change_link = True


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display  = ["product", "color", "stock", "updated_at"]
    list_filter   = ["product"]
    search_fields = ["product__name", "color"]
    readonly_fields = ["stock"]
    inlines       = [ProductSizeInline]


@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display  = ["variant", "size", "quantity"]
    list_filter   = ["variant__product", "variant__color"]
    search_fields = ["variant__product__name", "variant__color", "size"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ["name", "category", "price", "is_available_display", "in_stock", "featured", "trending", "created_at"]
    list_filter   = ["category", "in_stock", "featured", "trending"]
    search_fields = ["name", "description"]
    inlines       = [ProductVariantInline]

    def is_available_display(self, obj):
        return obj.is_available
    is_available_display.short_description = "متاح للبيع"
    is_available_display.boolean = True


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount", "discount_type", "uses", "max_uses", "active", "expiry"]
    list_filter  = ["active", "discount_type"]


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ["governorate", "fee", "enabled", "order"]
    list_editable = ["fee", "enabled", "order"]
    ordering     = ["order", "governorate"]


class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra  = 0
    fields = ["product", "name", "price", "quantity", "size", "color"]
    readonly_fields = ["line_total"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ["id", "first_name", "last_name", "phone", "city", "total", "status", "payment_method", "created_at"]
    list_filter   = ["status", "payment_method", "city"]
    search_fields = ["first_name", "last_name", "phone"]
    inlines       = [OrderItemInline]
    readonly_fields = ["subtotal", "shipping_fee", "tax", "total", "discount_amount"]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "quantity", "size", "color", "added_at"]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "added_at"]


@admin.register(StoreSetting)
class StoreSettingAdmin(admin.ModelAdmin):
    list_display = ["key", "value"]
