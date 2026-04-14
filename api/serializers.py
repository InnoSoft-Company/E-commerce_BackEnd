import json
from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Category, Product, ProductVariant, ProductSize,
    Order, OrderItem, Coupon, CartItem, WishlistItem, StoreSetting, ShippingZone
)

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


# ── ProductSize ───────────────────────────────────
class ProductSizeSerializer(serializers.ModelSerializer):
    """Read serializer for a size entry inside a variant."""
    class Meta:
        model  = ProductSize
        fields = ["id", "size", "quantity"]


class ProductSizeWriteSerializer(serializers.Serializer):
    """Used when creating/updating variants — accepts size + quantity pairs."""
    size     = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=0)


# ── ProductVariant ────────────────────────────────
class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Read serializer for a color variant.
    Only returns sizes that still have stock > 0.
    The variant itself is excluded from the product listing if stock == 0.
    """
    sizes       = serializers.SerializerMethodField()
    image       = serializers.SerializerMethodField()
    total_stock = serializers.IntegerField(source="stock", read_only=True)

    class Meta:
        model  = ProductVariant
        fields = ["id", "color", "color_hex", "image", "total_stock", "sizes"]

    def _build_url(self, path):
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
        return self._build_url(obj.image) if obj.image else None

    def get_sizes(self, obj):
        """Return only sizes with quantity > 0."""
        sizes = obj.sizes.filter(quantity__gt=0)
        return ProductSizeSerializer(sizes, many=True).data


class ProductVariantWriteSerializer(serializers.Serializer):
    """
    Accepts a full variant definition for create/update:
    {
        "color": "أسود",
        "color_hex": "#000000",       # optional
        "image": "<file or path>",    # optional
        "sizes": [
            {"size": "S",  "quantity": 5},
            {"size": "M",  "quantity": 3},
            {"size": "XL", "quantity": 0}
        ]
    }
    """
    color     = serializers.CharField(max_length=100)
    color_hex = serializers.CharField(max_length=7, required=False, allow_blank=True, default="")
    image     = serializers.CharField(required=False, allow_blank=True, default="")
    sizes     = ProductSizeWriteSerializer(many=True, required=False, default=list)


# ── Product ───────────────────────────────────────
class ProductSerializer(serializers.ModelSerializer):
    """
    Full read serializer for products with variant support.
    
    Response structure:
    - variants: Array of colors, each with sizes and stock info (only colors with stock > 0)
    - is_available: Boolean — computed from variants or legacy in_stock field
    - image: Product main image URL
    - sizes/colors: Legacy fields (empty arrays) — kept for backward compatibility
    
    Example response:
    {
        "id": 1,
        "name": "T-Shirt",
        "price": "29.99",
        "category": 5,
        "category_name": "Clothing",
        "image": "http://localhost:8000/media/products/tshirt.jpg",
        "variants": [
            {
                "id": 1,
                "color": "أسود (Black)",
                "color_hex": "#000000",
                "image": "http://localhost:8000/media/products/variants/black.jpg",
                "total_stock": 12,
                "sizes": [
                    {"id": 1, "size": "S", "quantity": 5},
                    {"id": 2, "size": "M", "quantity": 7}
                ]
            }
        ],
        "is_available": true,
        "rating": 4.5,
        "reviews": 23
    }
    """
    category_name = serializers.CharField(source="category.name", read_only=True)
    image         = serializers.SerializerMethodField()
    variants      = serializers.SerializerMethodField()
    is_available  = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "id", "name", "price", "category", "category_name",
            "image", "description",
            "variants",                 # NEW — structured: color → sizes → quantities + stock
            "is_available",             # NEW — computed availability
            "rating", "reviews",
            "in_stock", "featured", "trending",
            "created_at", "updated_at",
        ]

    def _build_url(self, path):
        """Convert relative paths to full URLs (handles both http and file paths)."""
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



    def get_variants(self, obj):
        """
        Return only variants (colors) that have at least 1 unit in stock.
        Each variant includes all sizes and their quantities.
        """
        available = obj.variants.filter(stock__gt=0).prefetch_related("sizes")
        return ProductVariantSerializer(
            available, many=True, context=self.context
        ).data

    def get_is_available(self, obj):
        """Product is available if it has at least one variant with stock > 0."""
        return obj.is_available


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Handles product creation/update. Supports both FormData and JSON.
    
    ✓ FORM DATA EXAMPLE (multipart/form-data):
    ────────────────────────────────────────────
    name                 = "T-Shirt"
    price                = "29.99"
    category             = "5" or "Clothing"
    image                = <file>
    description          = "Nice t-shirt"
    featured             = "true"
    variants             = '[
        {
            "color": "أسود",
            "color_hex": "#000000",
            "image": "path/or/url.jpg",
            "sizes": [
                {"size": "S", "quantity": 5},
                {"size": "M", "quantity": 10},
                {"size": "L", "quantity": 7}
            ]
        },
        {
            "color": "أبيض",
            "color_hex": "#FFFFFF",
            "image": "path/or/url.jpg",
            "sizes": [
                {"size": "S", "quantity": 3},
                {"size": "M", "quantity": 8}
            ]
        }
    ]'
    variant_image_أسود   = <file for black color image>  (optional)
    variant_image_أبيض   = <file for white color image>  (optional)
    
    ✓ JSON EXAMPLE (application/json):
    ────────────────────────────────────
    {
        "name": "T-Shirt",
        "price": "29.99",
        "category": 5,
        "image": "http://example.com/image.jpg",
        "description": "Nice t-shirt",
        "featured": true,
        "variants": [...]  // Same as above
    }
    
    NOTES:
    - category: Can be an ID or name (will lookup automatically)
    - image: URL or file upload
    - variants: JSON string containing array of color variants
    - Each variant has:
      * color (required): Color name
      * color_hex (optional): Hex code like #000000
      * image (optional): URL or path to variant image
      * sizes (optional): Array of {size, quantity} pairs
    """
    category    = serializers.CharField(
        help_text="Category ID or name (e.g., 5 or 'Clothing')"
    )
    image       = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Main product image URL or upload via FormData"
    )
    description = serializers.CharField(
        required=False, allow_blank=True, default="",
        help_text="Product description"
    )
    in_stock    = serializers.BooleanField(
        required=False, default=True,
        help_text="Legacy field (use variants for stock control)"
    )
    featured    = serializers.BooleanField(required=False, default=False)
    trending    = serializers.BooleanField(required=False, default=False)
    sizes       = serializers.CharField(
        required=False, allow_blank=True, default="[]",
        help_text="Legacy field (use variants instead)"
    )
    colors      = serializers.CharField(
        required=False, allow_blank=True, default="[]",
        help_text="Legacy field (use variants instead)"
    )
    variants    = serializers.CharField(
        required=False, allow_blank=True, default="[]",
        help_text="JSON array of color variants with sizes and quantities"
    )

    class Meta:
        model  = Product
        fields = [
            "name", "price", "category", "image",
            "description", "sizes", "colors", "variants",
            "in_stock", "featured", "trending",
        ]

    def to_internal_value(self, data):
        if hasattr(data, "getlist"):
            result = {}
            for key in data.keys():
                val = data.get(key)
                result[key] = val
        else:
            result = dict(data)

        # Handle image field
        request = self.context.get("request")
        image_file = None
        if request and hasattr(request, "FILES"):
            image_file = request.FILES.get("image")

        if image_file:
            from django.core.files.storage import default_storage
            filename = f"products/{image_file.name}"
            path = default_storage.save(filename, image_file)
            result["image"] = path
        elif result.get("image") and not isinstance(result["image"], str):
            img_obj = result["image"]
            if hasattr(img_obj, "read"):
                from django.core.files.storage import default_storage
                filename = f"products/{img_obj.name}"
                path = default_storage.save(filename, img_obj)
                result["image"] = path
        elif not result.get("image"):
            result["image"] = ""

        # Parse JSON strings for sizes/colors
        for field in ("sizes", "colors"):
            val = result.get(field, "[]")
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    result[field] = json.dumps(parsed if isinstance(parsed, list) else [])
                except Exception:
                    result[field] = "[]"
            elif isinstance(val, list):
                result[field] = json.dumps(val)
            else:
                result[field] = "[]"

        # Parse variants JSON
        val = result.get("variants", "[]")
        if isinstance(val, list):
            result["variants"] = json.dumps(val)
        elif not isinstance(val, str):
            result["variants"] = "[]"

        # Parse boolean strings
        for field in ("in_stock", "featured", "trending"):
            val = result.get(field)
            if isinstance(val, str):
                result[field] = val.lower() in ("true", "1", "yes")

        return super().to_internal_value(result)

    def validate_category(self, value):
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

    def _save_variant_image(self, request, color_key, fallback_path):
        """
        Look for a per-variant image file in request.FILES.
        Convention: field name = "variant_image_<color>" or "variant_image_<index>"
        Falls back to the path string passed from JSON.
        """
        if not request:
            return fallback_path
        field = f"variant_image_{color_key}"
        img_file = request.FILES.get(field)
        if img_file:
            from django.core.files.storage import default_storage
            filename = f"products/variants/{img_file.name}"
            return default_storage.save(filename, img_file)
        return fallback_path

    def _handle_variants(self, product, variants_json, request):
        """
        Parse the variants JSON and create/update ProductVariant + ProductSize records.
        variants_json is a JSON string like:
        [
            {
                "color": "أسود",
                "color_hex": "#000000",
                "image": "",
                "sizes": [
                    {"size": "S", "quantity": 5},
                    {"size": "M", "quantity": 0}
                ]
            }
        ]
        """
        try:
            variants_data = json.loads(variants_json) if isinstance(variants_json, str) else variants_json
        except Exception:
            return

        if not isinstance(variants_data, list) or len(variants_data) == 0:
            return

        # Validate using write serializer
        seen_colors = set()
        for idx, vdata in enumerate(variants_data):
            color = vdata.get("color", "").strip()
            if not color:
                continue
            if color in seen_colors:
                continue
            seen_colors.add(color)

            color_hex = vdata.get("color_hex", "")
            image_path = self._save_variant_image(request, color, vdata.get("image", ""))

            variant, _ = ProductVariant.objects.get_or_create(
                product=product,
                color=color,
                defaults={"color_hex": color_hex, "image": image_path, "stock": 0}
            )
            # Always update hex/image on update
            variant.color_hex = color_hex
            if image_path:
                variant.image = image_path
            variant.save(update_fields=["color_hex", "image"])

            # Handle sizes
            sizes_data = vdata.get("sizes", [])
            for sdata in sizes_data:
                size_name = sdata.get("size", "").strip()
                qty = int(sdata.get("quantity", 0))
                if not size_name:
                    continue
                psize, _ = ProductSize.objects.get_or_create(
                    variant=variant,
                    size=size_name,
                    defaults={"quantity": qty}
                )
                # Always update quantity
                psize.quantity = qty
                psize.save(update_fields=["quantity"])

            # Recalculate variant total stock
            variant.recalculate_stock()

        # After all variants are processed, sync product in_stock
        product.sync_in_stock()

    def create(self, validated_data):
        request       = self.context.get("request")
        variants_json = validated_data.pop("variants", "[]")
        
        # Remove legacy fields — they're not part of the Product model anymore
        validated_data.pop("sizes", None)
        validated_data.pop("colors", None)

        product = Product.objects.create(**validated_data)

        # Gallery images
        paths = self._save_gallery(request)
        if paths:
            product.images = paths
            product.save(update_fields=["images"])

        # Variants
        self._handle_variants(product, variants_json, request)

        return product

    def update(self, instance, validated_data):
        request       = self.context.get("request")
        variants_json = validated_data.pop("variants", None)
        
        # Remove legacy fields — they're not part of the Product model anymore
        validated_data.pop("sizes", None)
        validated_data.pop("colors", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        paths = self._save_gallery(request)
        if paths:
            instance.images = paths

        instance.save()

        if variants_json is not None:
            self._handle_variants(instance, variants_json, request)

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
    product    = ProductSerializer(read_only=True)
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
