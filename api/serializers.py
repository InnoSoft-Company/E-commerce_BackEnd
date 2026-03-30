import json
from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, Product, Order, OrderItem, Coupon, CartItem, WishlistItem, StoreSetting, ShippingZone

User = get_user_model()


# ── Auth ──────────────────────────────────────────
class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)
    phone     = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone", "password", "password2"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password": "كلمتا المرور غير متطابقتين"})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        username = validated_data.get("username", "")
        if User.objects.filter(username=username).exists():
            import time
            validated_data["username"] = username.split("@")[0] + "_" + str(int(time.time()))
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone", "address", "city", "country", "is_admin", "is_staff"]
        read_only_fields = ["id", "is_admin", "is_staff"]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ["first_name", "last_name", "email", "phone", "address", "city", "country"]


# ── Category ──────────────────────────────────────
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ["id", "name", "name_ar", "slug", "image", "count"]


# ── ShippingZone ──────────────────────────────────
class ShippingZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ShippingZone
        fields = ["id", "governorate", "fee", "enabled", "order"]


# ── Product ───────────────────────────────────────
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    image         = serializers.SerializerMethodField()
    images        = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "id", "name", "price", "category", "category_name",
            "image", "images", "description",
            "sizes", "colors", "rating", "reviews",
            "in_stock", "featured", "trending",
            "created_at", "updated_at",
        ]

    def _build_url(self, path):
        """Convert relative media path to absolute URL."""
        if not path:
            return path
        if path.startswith("http://") or path.startswith("https://"):
            return path
        request = self.context.get("request")
        base = "http://localhost:8000"
        if request:
            base = request.build_absolute_uri("/").rstrip("/")
        if not path.startswith("/"):
            path = "/media/" + path
        return base + path

    def get_image(self, obj):
        return self._build_url(obj.image)

    def get_images(self, obj):
        return [self._build_url(p) for p in (obj.images or [])]


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Handles product creation/update via FormData or JSON.
    Accepts:
    - image: File upload OR URL string
    - images: list of File uploads (gallery)
    - sizes/colors: JSON strings (from FormData) will be parsed
    """
    category    = serializers.CharField()
    image       = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    in_stock    = serializers.BooleanField(required=False, default=True)
    featured    = serializers.BooleanField(required=False, default=False)
    trending    = serializers.BooleanField(required=False, default=False)
    sizes       = serializers.CharField(required=False, allow_blank=True, default="[]")
    colors      = serializers.CharField(required=False, allow_blank=True, default="[]")

    class Meta:
        model  = Product
        fields = [
            "name", "price", "category", "image",
            "description", "sizes", "colors",
            "in_stock", "featured", "trending",
        ]

    def to_internal_value(self, data):
        """
        Process FormData and JSON requests:
        - Parse image (File or URL string)
        - Parse JSON strings for sizes/colors
        - Parse boolean strings from FormData
        """
        # Convert QueryDict to plain dict
        if hasattr(data, "getlist"):
            result = {}
            for key in data.keys():
                val = data.get(key)
                result[key] = val
        else:
            result = dict(data)

        # Handle image field - check request.FILES first (FormData uploads)
        request = self.context.get("request")
        image_file = None
        if request and hasattr(request, "FILES"):
            image_file = request.FILES.get("image")
        
        if image_file:
            # Save uploaded file
            from django.core.files.storage import default_storage
            filename = f"products/{image_file.name}"
            path = default_storage.save(filename, image_file)
            result["image"] = path
        elif result.get("image") and not isinstance(result["image"], str):
            # Fallback: if image is somehow a File object in data, convert it
            img_obj = result["image"]
            if hasattr(img_obj, "read"):
                from django.core.files.storage import default_storage
                filename = f"products/{img_obj.name}"
                path = default_storage.save(filename, img_obj)
                result["image"] = path
        elif not result.get("image"):
            result["image"] = ""

        # Parse JSON strings for sizes/colors (from FormData)
        for field in ("sizes", "colors"):
            val = result.get(field, "[]")
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    result[field] = json.dumps(parsed if isinstance(parsed, list) else [])
                except:
                    result[field] = "[]"
            elif isinstance(val, list):
                # Convert list to JSON string
                result[field] = json.dumps(val)
            else:
                result[field] = "[]"

        # Parse boolean strings from FormData
        for field in ("in_stock", "featured", "trending"):
            val = result.get(field)
            if isinstance(val, str):
                result[field] = val.lower() in ("true", "1", "yes")

        return super().to_internal_value(result)

    def validate_category(self, value):
        from .models import Category
        if str(value).isdigit():
            try:
                return Category.objects.get(pk=int(value))
            except Category.DoesNotExist:
                raise serializers.ValidationError(f"Category id {value} not found")
        try:
            return Category.objects.get(name__iexact=str(value))
        except Category.DoesNotExist:
            raise serializers.ValidationError(f"Category '{value}' not found")

    def _save_gallery(self, request):
        """Extract and save gallery image files from the request."""
        if not request:
            return []
        files = request.FILES.getlist("images")
        paths = []
        for img_file in files:
            from django.core.files.storage import default_storage
            filename = f"products/{img_file.name}"
            path = default_storage.save(filename, img_file)
            paths.append(path)
        return paths

    def create(self, validated_data):
        request = self.context.get("request")
        product = Product.objects.create(**validated_data)
        paths   = self._save_gallery(request)
        if paths:
            product.images = paths
            product.save()
        return product

    def update(self, instance, validated_data):
        request = self.context.get("request")
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        paths = self._save_gallery(request)
        if paths:
            instance.images = paths
        instance.save()
        return instance


# ── Coupon ────────────────────────────────────────
class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Coupon
        fields = ["id", "code", "discount", "discount_type", "uses", "max_uses", "active", "expiry", "created_at"]
        read_only_fields = ["id", "uses", "created_at"]


class CouponValidateSerializer(serializers.Serializer):
    code     = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)


# ── Order ─────────────────────────────────────────
class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()

    class Meta:
        model  = OrderItem
        fields = ["id", "product", "name", "price", "quantity", "size", "color", "image", "line_total"]


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    name       = serializers.CharField()
    price      = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity   = serializers.IntegerField(min_value=1)
    size       = serializers.CharField(required=False, allow_blank=True, default="")
    color      = serializers.CharField(required=False, allow_blank=True, default="")
    image      = serializers.CharField(required=False, allow_blank=True, default="")


class OrderSerializer(serializers.ModelSerializer):
    items           = OrderItemSerializer(many=True, read_only=True)
    status_display  = serializers.CharField(source="get_status_display", read_only=True)
    payment_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    customer_name   = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = [
            "id", "user", "customer_name",
            "first_name", "last_name", "email", "phone",
            "address", "city", "zip_code",
            "subtotal", "shipping_fee", "tax", "total",
            "discount_amount", "coupon",
            "status", "status_display",
            "payment_method", "payment_display",
            "items", "created_at", "updated_at",
        ]

    def get_customer_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class OrderCreateSerializer(serializers.Serializer):
    first_name     = serializers.CharField()
    last_name      = serializers.CharField()
    email          = serializers.EmailField(required=False, allow_blank=True, default="")
    phone          = serializers.CharField()
    address        = serializers.CharField(required=False, allow_blank=True, default="")
    city           = serializers.CharField()
    zip_code       = serializers.CharField(required=False, allow_blank=True, default="")
    payment_method = serializers.ChoiceField(choices=["deposit","vodafone","instapay","bank","card"])
    coupon_code    = serializers.CharField(required=False, allow_blank=True, default="")
    shipping_fee   = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal("0"))
    items          = OrderItemCreateSerializer(many=True)


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["processing","shipping","delivered","cancelled"])


# ── Cart ──────────────────────────────────────────
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    line_total = serializers.ReadOnlyField()

    class Meta:
        model  = CartItem
        fields = ["id", "product", "quantity", "size", "color", "line_total", "added_at", "updated_at"]
        read_only_fields = ["id", "added_at", "updated_at"]


class CartItemCreateUpdateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model  = CartItem
        fields = ["id", "product_id", "quantity", "size", "color"]
        read_only_fields = ["id"]


# ── Wishlist ──────────────────────────────────────
class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model  = WishlistItem
        fields = ["id", "product", "added_at"]


# ── Store Settings ────────────────────────────────
class StoreSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StoreSetting
        fields = ["key", "value"]
