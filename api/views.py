from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from rest_framework import generics, viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal

from .models import (
    Category, Product, ProductVariant, ProductSize,
    Order, OrderItem, Coupon, CartItem, WishlistItem, StoreSetting, ShippingZone
)
from .serializers import (
    RegisterSerializer, UserSerializer, UserProfileUpdateSerializer,
    CategorySerializer,
    ShippingZoneSerializer,
    ProductSerializer, ProductWriteSerializer,
    ProductVariantSerializer,
    CouponSerializer, CouponValidateSerializer,
    OrderSerializer, OrderCreateSerializer, OrderStatusUpdateSerializer,
    CartItemSerializer, CartItemCreateUpdateSerializer,
    WishlistItemSerializer,
    StoreSettingSerializer,
)

User = get_user_model()


# ═══════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════
class RegisterView(generics.CreateAPIView):
    serializer_class   = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user    = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user":   UserSerializer(user).data,
            "tokens": {
                "access":  str(refresh.access_token),
                "refresh": str(refresh),
            },
        }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        token = RefreshToken(request.data.get("refresh"))
        token.blacklist()
    except Exception:
        pass
    return Response({"detail": "تم تسجيل الخروج"})


# ═══════════════════════════════════════════════
#  CATEGORIES
# ═══════════════════════════════════════════════
class CategoryViewSet(viewsets.ModelViewSet):
    queryset         = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdminUser()]


# ═══════════════════════════════════════════════
#  SHIPPING ZONES
# ═══════════════════════════════════════════════
class ShippingZoneViewSet(viewsets.ModelViewSet):
    queryset         = ShippingZone.objects.all()
    serializer_class = ShippingZoneSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdminUser()]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_admin)):
            qs = qs.filter(enabled=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# ═══════════════════════════════════════════════
#  PRODUCTS
# ═══════════════════════════════════════════════
class ProductViewSet(viewsets.ModelViewSet):
    """
    Products with variant-aware availability.

    Public list/retrieve: only returns products that are available
    (has at least one variant with stock > 0, or legacy in_stock=True).

    Admin list/retrieve: returns all products regardless of availability.
    """

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ProductWriteSerializer
        return ProductSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_queryset(self):
        user   = self.request.user
        is_admin = user.is_authenticated and (user.is_staff or getattr(user, "is_admin", False))

        qs = Product.objects.select_related("category").prefetch_related(
            "variants", "variants__sizes"
        )

        # ── Availability filter ──────────────────────────────────────────────
        # Public users only see products that have stock.
        # Products with variants: at least 1 variant with stock > 0.
        # Products without variants: use legacy in_stock flag.
        if not is_admin:
            # Products with variants that have stock > 0
            has_available_variants = Q(variants__stock__gt=0)
            # Products without variants that are in_stock
            no_variants_in_stock   = Q(variants__isnull=True, in_stock=True)
            qs = qs.filter(has_available_variants | no_variants_in_stock).distinct()

        params = self.request.query_params

        category = params.get("category")
        if category:
            qs = qs.filter(category__name__iexact=category)

        search = params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        if params.get("featured") == "true":
            qs = qs.filter(featured=True)

        if params.get("trending") == "true":
            qs = qs.filter(trending=True)

        sort = params.get("sort", "newest")
        if sort == "price_low":
            qs = qs.order_by("price")
        elif sort == "price_high":
            qs = qs.order_by("-price")
        elif sort == "popular":
            qs = qs.order_by("-reviews")
        else:
            qs = qs.order_by("-created_at")

        min_price = params.get("min_price")
        max_price = params.get("max_price")
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ProductSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial    = kwargs.pop("partial", False)
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance   = serializer.save()
        return Response(ProductSerializer(instance, context={"request": request}).data)

    # ── Variant sub-endpoints ──────────────────────────────────────────────
    @action(
        detail=True, methods=["get"],
        url_path="variants", permission_classes=[AllowAny]
    )
    def variants(self, request, pk=None):
        """
        GET /products/<id>/variants/
        
        Returns all color variants for a product, each with its sizes and stock info.
        
        RESPONSE EXAMPLE:
        [
            {
                "id": 1,
                "color": "أسود",
                "color_hex": "#000000",
                "image": "http://localhost:8000/media/products/variants/black.jpg",
                "total_stock": 12,
                "sizes": [
                    {"id": 1, "size": "S", "quantity": 5},
                    {"id": 2, "size": "M", "quantity": 7}
                ]
            }
        ]
        
        BEHAVIOR:
        - Public users: only see variants with stock > 0
        - Admins: see all variants including out-of-stock ones
        """
        product  = self.get_object()
        user     = request.user
        is_admin = user.is_authenticated and (user.is_staff or getattr(user, "is_admin", False))

        qs = product.variants.prefetch_related("sizes")
        if not is_admin:
            qs = qs.filter(stock__gt=0)

        return Response(
            ProductVariantSerializer(qs, many=True, context={"request": request}).data
        )

    @action(
        detail=True, methods=["post", "put", "patch"],
        url_path="variants/update", permission_classes=[IsAdminUser]
    )
    def update_variants(self, request, pk=None):
        """
        POST/PUT /products/<id>/variants/update/
        
        Add or update all color variants for a product (admin only).
        This REPLACES all existing variants with the new data.
        
        REQUEST BODY (application/json):
        {
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
        
        RESPONSE: Updated product with new variants
        
        NOTES:
        - Duplicates by color are automatically skipped
        - Variant totals (stock) are recalculated automatically
        - Product availability is updated in real-time
        - Size quantity can be 0 (counts as out-of-stock for that size)
        """
        product = self.get_object()
        variants_data = request.data.get("variants", [])

        import json
        if isinstance(variants_data, str):
            try:
                variants_data = json.loads(variants_data)
            except Exception:
                variants_data = []

        write_ser = ProductWriteSerializer(context={"request": request})
        write_ser._handle_variants(product, json.dumps(variants_data), request)

        return Response(
            ProductSerializer(product, context={"request": request}).data
        )

    @action(
        detail=True, methods=["get"],
        url_path="stock", permission_classes=[AllowAny]
    )
    def stock(self, request, pk=None):
        """
        GET /products/<id>/stock/
        
        Detailed stock breakdown by color and size.
        Useful for showing "Only 3 left in stock!" style messages on frontend.
        
        RESPONSE EXAMPLE:
        {
            "product_id": 1,
            "product_name": "T-Shirt",
            "is_available": true,
            "colors": [
                {
                    "color": "أسود",
                    "color_hex": "#000000",
                    "image": "http://localhost:8000/media/products/variants/black.jpg",
                    "stock": 12,
                    "sizes": [
                        {"size": "S", "quantity": 5},
                        {"size": "M", "quantity": 7},
                        {"size": "L", "quantity": 0}
                    ]
                },
                {
                    "color": "أبيض",
                    "color_hex": "#FFFFFF",
                    "image": "http://localhost:8000/media/products/variants/white.jpg",
                    "stock": 8,
                    "sizes": [
                        {"size": "S", "quantity": 3},
                        {"size": "M", "quantity": 5}
                    ]
                }
            ]
        }
        
        BEHAVIOR:
        - Public users: only see colors/sizes with quantity > 0
        - Admins: see all colors/sizes including zero quantities
        """
        product  = self.get_object()
        user     = request.user
        is_admin = user.is_authenticated and (user.is_staff or getattr(user, "is_admin", False))

        qs = product.variants.prefetch_related("sizes").all()
        if not is_admin:
            qs = qs.filter(stock__gt=0)

        result = []
        for variant in qs:
            sizes = []
            for ps in variant.sizes.all():
                if is_admin or ps.quantity > 0:
                    sizes.append({
                        "size":     ps.size,
                        "quantity": ps.quantity,
                    })
            result.append({
                "color":     variant.color,
                "color_hex": variant.color_hex,
                "image":     variant.image,
                "stock":     variant.stock,
                "sizes":     sizes,
            })

        return Response({
            "product_id":   product.id,
            "product_name": product.name,
            "is_available": product.is_available,
            "colors":       result,
        })


# ═══════════════════════════════════════════════
#  COUPONS
# ═══════════════════════════════════════════════
class CouponViewSet(viewsets.ModelViewSet):
    queryset         = Coupon.objects.all().order_by("-created_at")
    serializer_class = CouponSerializer

    def get_permissions(self):
        if self.action == "validate":
            return [AllowAny()]
        return [IsAdminUser()]

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def validate(self, request):
        s = CouponValidateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        code     = s.validated_data["code"].upper()
        subtotal = s.validated_data["subtotal"]
        try:
            coupon = Coupon.objects.get(code=code, active=True)
        except Coupon.DoesNotExist:
            return Response({"valid": False, "error": "الكود غير صحيح أو منتهي"}, status=400)

        if coupon.expiry and coupon.expiry < timezone.now().date():
            return Response({"valid": False, "error": "انتهت صلاحية هذا الكود"}, status=400)

        if coupon.uses >= coupon.max_uses:
            return Response({"valid": False, "error": "تم استنفاد هذا الكود"}, status=400)

        if coupon.discount_type == "percent":
            discount = (subtotal * coupon.discount / 100).quantize(Decimal("0.01"))
        else:
            discount = min(coupon.discount, subtotal)

        return Response({
            "valid":           True,
            "code":            coupon.code,
            "discount_type":   coupon.discount_type,
            "discount":        str(coupon.discount),
            "discount_amount": str(discount),
        })


# ═══════════════════════════════════════════════
#  ORDERS
# ═══════════════════════════════════════════════
def _deduct_stock_for_order(order_items_data):
    """
    For each order item that specifies a color and size, find the
    corresponding ProductSize record and reduce its quantity.

    This is called inside a database transaction so if anything fails
    the whole order is rolled back.

    Returns a list of errors (empty list = all good).
    """
    errors = []
    for item in order_items_data:
        product_id = item.get("product_id")
        color      = (item.get("color") or "").strip()
        size       = (item.get("size") or "").strip()
        qty        = int(item.get("quantity", 1))

        if not color or not size:
            # No variant info → skip stock deduction (legacy product)
            continue

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            continue

        if not product.has_variants:
            continue

        try:
            variant = product.variants.get(color__iexact=color)
        except ProductVariant.DoesNotExist:
            errors.append(
                f"اللون '{color}' غير متوفر للمنتج '{product.name}'"
            )
            continue

        try:
            psize = variant.sizes.get(size__iexact=size)
        except ProductSize.DoesNotExist:
            errors.append(
                f"المقاس '{size}' غير متوفر للون '{color}' من منتج '{product.name}'"
            )
            continue

        try:
            psize.reduce_stock(qty)
        except ValueError as e:
            errors.append(str(e))

    return errors


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.action in ["list", "update_status", "dashboard_stats"]:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        if user.is_staff or getattr(user, "is_admin", False):
            qs = Order.objects.all().prefetch_related("items")
            s  = self.request.query_params.get("status")
            if s:
                qs = qs.filter(status=s)
            q = self.request.query_params.get("search")
            if q:
                qs = qs.filter(
                    Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                    Q(phone__icontains=q) | Q(pk__icontains=q)
                )
            return qs.order_by("-created_at")
        return Order.objects.filter(user=user).prefetch_related("items").order_by("-created_at")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        s = OrderCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        # ── Stock validation & deduction ──────────────────────────────────
        # Done first, inside a transaction, so any stock error prevents order creation.
        stock_errors = _deduct_stock_for_order(data["items"])
        if stock_errors:
            return Response(
                {"detail": "خطأ في المخزون", "errors": stock_errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Coupon ────────────────────────────────────────────────────────
        coupon          = None
        discount_amount = Decimal("0")
        coupon_code     = data.get("coupon_code", "").upper()
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, active=True)
            except Coupon.DoesNotExist:
                pass

        # ── Subtotal ──────────────────────────────────────────────────────
        subtotal = sum(
            Decimal(str(item["price"])) * item["quantity"]
            for item in data["items"]
        )

        # ── Shipping fee ──────────────────────────────────────────────────
        frontend_fee = data.get("shipping_fee")
        if frontend_fee and frontend_fee > 0:
            shipping_fee = frontend_fee
        else:
            try:
                zone         = ShippingZone.objects.get(governorate=data["city"], enabled=True)
                shipping_fee = zone.fee
            except ShippingZone.DoesNotExist:
                shipping_fee = Decimal("80")

        if subtotal >= Decimal("1000"):
            shipping_fee = Decimal("0")

        tax = Decimal("0")

        if coupon:
            if coupon.discount_type == "percent":
                discount_amount = (subtotal * coupon.discount / 100).quantize(Decimal("0.01"))
            else:
                discount_amount = min(coupon.discount, subtotal)
            coupon.uses += 1
            coupon.save()

        total = subtotal + shipping_fee + tax - discount_amount

        order = Order.objects.create(
            user            = request.user if request.user.is_authenticated else None,
            first_name      = data["first_name"],
            last_name       = data["last_name"],
            email           = data["email"],
            phone           = data["phone"],
            address         = data["address"],
            city            = data["city"],
            zip_code        = data.get("zip_code", ""),
            subtotal        = subtotal,
            shipping_fee    = shipping_fee,
            tax             = tax,
            total           = total,
            discount_amount = discount_amount,
            coupon          = coupon,
            payment_method  = data["payment_method"],
        )

        for item in data["items"]:
            product = None
            try:
                product = Product.objects.get(pk=item["product_id"])
            except Product.DoesNotExist:
                pass
            OrderItem.objects.create(
                order    = order,
                product  = product,
                name     = item["name"],
                price    = item["price"],
                quantity = item["quantity"],
                size     = item.get("size", ""),
                color    = item.get("color", ""),
                image    = item.get("image", ""),
            )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], permission_classes=[IsAdminUser])
    def update_status(self, request, pk=None):
        order = self.get_object()
        s     = OrderStatusUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order.status = s.validated_data["status"]
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def dashboard_stats(self, request):
        total_revenue  = Order.objects.filter(status="delivered").aggregate(t=Sum("total"))["t"] or 0
        total_orders   = Order.objects.count()
        total_products = Product.objects.count()
        total_users    = User.objects.count()
        by_status = {
            "delivered":  Order.objects.filter(status="delivered").count(),
            "shipping":   Order.objects.filter(status="shipping").count(),
            "processing": Order.objects.filter(status="processing").count(),
            "cancelled":  Order.objects.filter(status="cancelled").count(),
        }
        recent = Order.objects.order_by("-created_at")[:5]
        return Response({
            "total_revenue":  str(total_revenue),
            "total_orders":   total_orders,
            "total_products": total_products,
            "total_users":    total_users,
            "by_status":      by_status,
            "recent_orders":  OrderSerializer(recent, many=True).data,
        })


# ═══════════════════════════════════════════════
#  CART
# ═══════════════════════════════════════════════
class CartItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class    = CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related("product")

    def get_serializer_class(self):
        if self.action in ["create", "partial_update"]:
            return CartItemCreateUpdateSerializer
        return CartItemSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def total(self, request):
        items = CartItem.objects.filter(user=request.user)
        total = sum(float(item.product.price) * item.quantity for item in items)
        return Response({
            "count": items.count(),
            "total": str(total),
            "items": CartItemSerializer(items, many=True).data,
        })

    @action(detail=False, methods=["delete"])
    def clear(self, request):
        CartItem.objects.filter(user=request.user).delete()
        return Response({"detail": "تم تفريغ السلة"})


# ═══════════════════════════════════════════════
#  WISHLIST
# ═══════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wishlist_list(request):
    items = WishlistItem.objects.filter(user=request.user).select_related("product")
    return Response(WishlistItemSerializer(items, many=True, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def wishlist_add(request):
    product_id = request.data.get("product_id")
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"error": "المنتج غير موجود"}, status=404)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    return Response(WishlistItemSerializer(item, context={"request": request}).data, status=201 if created else 200)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def wishlist_remove(request, product_id):
    WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
    return Response(status=204)


# ═══════════════════════════════════════════════
#  ADMIN — USERS
# ═══════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    search = request.query_params.get("search", "")
    qs = User.objects.all()
    if search:
        qs = qs.filter(
            Q(username__icontains=search) | Q(email__icontains=search) | Q(first_name__icontains=search)
        )
    users = qs.annotate(order_count=Count("orders")).order_by("-date_joined")
    data = []
    for u in users:
        d = UserSerializer(u).data
        d["order_count"] = u.order_count
        d["total_spent"] = str(Order.objects.filter(user=u).aggregate(t=Sum("total"))["t"] or 0)
        d["date_joined"] = u.date_joined.strftime("%B %Y")
        data.append(d)
    return Response(data)


# ═══════════════════════════════════════════════
#  STORE SETTINGS
# ═══════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAdminUser])
def settings_list(request):
    items = StoreSetting.objects.all()
    data  = {s.key: s.value for s in items}
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def settings_update(request):
    for key, value in request.data.items():
        StoreSetting.objects.update_or_create(key=key, defaults={"value": value})
    return Response({"detail": "تم حفظ الإعدادات"})
