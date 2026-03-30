from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Category, Product, Order, OrderItem, Coupon, WishlistItem, StoreSetting, ShippingZone


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("بيانات إضافية", {"fields": ("phone", "address", "city", "country", "is_admin")}),
    )
    list_display  = ["username", "email", "first_name", "last_name", "is_staff", "is_admin"]
    list_filter   = ["is_staff", "is_admin", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ["name", "name_ar", "slug", "count"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ["name", "price", "category", "in_stock", "featured", "trending", "created_at"]
    list_filter   = ["category", "in_stock", "featured", "trending"]
    search_fields = ["name", "description"]
    list_editable = ["in_stock", "featured", "trending"]


class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra  = 0
    fields = ["name", "price", "quantity", "size", "color"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ["__str__", "city", "total", "status", "payment_method", "created_at"]
    list_filter   = ["status", "payment_method"]
    search_fields = ["first_name", "last_name", "phone", "email"]
    list_editable = ["status"]
    inlines       = [OrderItemInline]
    readonly_fields = ["subtotal", "shipping_fee", "tax", "total", "discount_amount", "coupon", "created_at"]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ["code", "discount", "discount_type", "uses", "max_uses", "active", "expiry"]
    list_editable = ["active"]


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display  = ["governorate", "fee", "enabled", "order"]
    list_editable = ["fee", "enabled", "order"]
    ordering      = ["order", "governorate"]


@admin.register(StoreSetting)
class StoreSettingAdmin(admin.ModelAdmin):
    list_display = ["key", "value"]


admin.site.register(WishlistItem)
