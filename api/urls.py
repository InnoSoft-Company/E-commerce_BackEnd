from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    # Auth
    RegisterView, me_view, update_profile_view, logout_view,
    # ViewSets
    CategoryViewSet, ProductViewSet, CouponViewSet, OrderViewSet, ShippingZoneViewSet, CartItemViewSet,
    # Cart & Wishlist
    wishlist_list, wishlist_add, wishlist_remove,
    # Admin
    admin_users_list, settings_list, settings_update,
)

router = DefaultRouter()
router.register("categories",     CategoryViewSet,    basename="category")
router.register("products",       ProductViewSet,     basename="product")
router.register("coupons",        CouponViewSet,      basename="coupon")
router.register("orders",         OrderViewSet,       basename="order")
router.register("shipping-zones", ShippingZoneViewSet, basename="shipping-zone")
router.register("cart",           CartItemViewSet,    basename="cart")

urlpatterns = [
    # ── Auth ────────────────────────────────────
    path("auth/register/",         RegisterView.as_view(),        name="register"),
    path("auth/login/",            TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/",          TokenRefreshView.as_view(),    name="token_refresh"),
    path("auth/logout/",           logout_view,                   name="logout"),
    path("auth/me/",               me_view,                       name="me"),
    path("auth/me/update/",        update_profile_view,           name="update_profile"),

    # ── Wishlist ─────────────────────────────────
    path("wishlist/",              wishlist_list,  name="wishlist_list"),
    path("wishlist/add/",          wishlist_add,   name="wishlist_add"),
    path("wishlist/remove/<int:product_id>/", wishlist_remove, name="wishlist_remove"),

    # ── Admin ────────────────────────────────────
    path("admin/users/",           admin_users_list, name="admin_users"),
    path("admin/settings/",        settings_list,    name="settings_get"),
    path("admin/settings/update/", settings_update,  name="settings_update"),

    # ── Router (CRUD + shipping-zones) ───────────
    path("", include(router.urls)),
]
