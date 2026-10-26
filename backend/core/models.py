"""Phase 1 schema. Business writes will go through transaction services in phase 2."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


class Timestamps(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Store(Timestamps):
    name = models.CharField(max_length=150)
    address = models.TextField()
    opening_hours = models.CharField(max_length=120, default="08:00–20:00")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class EmailUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El correo es obligatorio")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superusuario requiere is_staff e is_superuser")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        OWNER = "OWNER", "Dueño"
        EMPLOYEE = "EMPLOYEE", "Empleado"
        CUSTOMER = "CUSTOMER", "Cliente"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=8, choices=Role.choices)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.PROTECT, related_name="staff")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = EmailUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
            models.UniqueConstraint(fields=["store"], condition=Q(role="OWNER", is_active=True), name="one_active_owner_per_store"),
            models.CheckConstraint(condition=(Q(role__in=["OWNER", "EMPLOYEE"], store__isnull=False) | Q(role__in=["ADMIN", "CUSTOMER"], store__isnull=True)), name="user_role_store_consistent"),
        ]

    def clean(self):
        super().clean()
        self.email = self.email.lower().strip()
        if self.role in (self.Role.OWNER, self.Role.EMPLOYEE) and not self.store_id:
            raise ValidationError({"store": "El personal requiere bodega"})
        if self.role in (self.Role.ADMIN, self.Role.CUSTOMER) and self.store_id:
            raise ValidationError({"store": "Este rol no pertenece a una bodega"})
        if self.is_superuser and (self.role != self.Role.ADMIN or not self.is_staff):
            raise ValidationError("Superusuario debe ser administrador activo de Django")


class Product(Timestamps):
    class Unit(models.TextChoices):
        GRAM = "G", "Gramos"
        UNIT = "UNIT", "Unidades"

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="products")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=4, choices=Unit.choices)
    sale_step = models.PositiveBigIntegerField()
    reference_price = models.DecimalField(max_digits=14, decimal_places=2)
    storage_conditions = models.TextField()
    photo_path = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "code"], name="product_code_per_store"),
            models.CheckConstraint(condition=Q(sale_step__gt=0), name="product_step_positive"),
            models.CheckConstraint(condition=Q(reference_price__gt=0), name="product_price_positive"),
        ]


class Lot(Timestamps):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="lots")
    code = models.CharField(max_length=80)
    received_date = models.DateField()
    expiry_date = models.DateField()
    sales_close_at = models.DateTimeField()
    total_cost = models.DecimalField(max_digits=14, decimal_places=2)
    received_qty = models.PositiveBigIntegerField()
    physical_qty = models.PositiveBigIntegerField(default=0)
    reserved_qty = models.PositiveBigIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "code"], name="lot_code_per_product"),
            models.CheckConstraint(condition=Q(received_qty__gt=0), name="lot_received_positive"),
            models.CheckConstraint(condition=Q(total_cost__gte=0), name="lot_cost_nonnegative"),
            models.CheckConstraint(condition=Q(physical_qty__gte=0), name="lot_physical_nonnegative"),
            models.CheckConstraint(condition=Q(reserved_qty__gte=0), name="lot_reserved_nonnegative"),
            models.CheckConstraint(condition=Q(reserved_qty__lte=F("physical_qty")), name="lot_reserve_not_above_physical"),
            models.CheckConstraint(condition=Q(expiry_date__gte=F("received_date") + timedelta(days=7)), name="lot_min_seven_days"),
        ]

    @property
    def available_qty(self):
        return self.physical_qty - self.reserved_qty

    def clean(self):
        super().clean()
        if self.received_date and self.expiry_date and self.expiry_date - self.received_date < timedelta(days=7):
            raise ValidationError({"expiry_date": "La duración mínima es 7 días"})
        if self.sales_close_at and self.expiry_date and self.sales_close_at.date() >= self.expiry_date:
            raise ValidationError({"sales_close_at": "La venta debe cerrar antes del vencimiento"})


class Offer(Timestamps):
    class State(models.TextChoices):
        DRAFT = "DRAFT"
        PUBLISHED = "PUBLISHED"
        PAUSED = "PAUSED"
        CLOSED = "CLOSED"

    lot = models.OneToOneField(Lot, on_delete=models.PROTECT, related_name="offer")
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    original_price = models.DecimalField(max_digits=14, decimal_places=2)
    current_price = models.DecimalField(max_digits=14, decimal_places=2)
    version = models.PositiveIntegerField(default=1)
    automation_paused = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(original_price__gt=0), name="offer_original_positive"),
            models.CheckConstraint(condition=Q(current_price__gt=0, current_price__lte=F("original_price")), name="offer_current_in_range"),
            models.CheckConstraint(condition=Q(version__gt=0), name="offer_version_positive"),
        ]


class Order(Timestamps):
    class State(models.TextChoices):
        PENDING = "PENDING"
        VERIFYING = "VERIFYING"
        PAID = "PAID"
        FAILED = "FAILED"
        EXPIRED = "EXPIRED"
        PAYMENT_REVIEW = "PAYMENT_REVIEW"

    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="orders")
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="PEN")
    reservation_until = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField(unique=True)
    request_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(total__gt=0), name="order_total_positive")]

    def clean(self):
        super().clean()
        if self.customer_id and self.customer.role != User.Role.CUSTOMER:
            raise ValidationError({"customer": "El comprador debe ser cliente"})
        if self.currency != "PEN":
            raise ValidationError({"currency": "La demo utiliza PEN"})


class OrderLine(Timestamps):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="lines")
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT)
    base_qty = models.PositiveBigIntegerField()
    step_snapshot = models.PositiveBigIntegerField()
    step_price_snapshot = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    expiry_snapshot = models.DateField()
    offer_version = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "offer"], name="orderline_offer_unique"),
            models.CheckConstraint(condition=Q(base_qty__gt=0, step_snapshot__gt=0, step_price_snapshot__gt=0, amount__gt=0), name="orderline_positive"),
        ]

    def clean(self):
        super().clean()
        if self.base_qty and self.step_snapshot and self.base_qty % self.step_snapshot:
            raise ValidationError({"base_qty": "Cantidad fuera del paso de venta"})
        if self.offer_id and self.order_id and self.offer.lot.product.store_id != self.order.store_id:
            raise ValidationError({"offer": "La oferta pertenece a otra bodega"})
        if self.base_qty and self.step_snapshot and self.step_price_snapshot and self.amount != Decimal(self.base_qty // self.step_snapshot) * self.step_price_snapshot:
            raise ValidationError({"amount": "Importe no coincide con cantidad y precio"})


class Reservation(Timestamps):
    class State(models.TextChoices):
        ACTIVE = "ACTIVE"
        CONSUMED = "CONSUMED"
        RELEASED = "RELEASED"

    line = models.OneToOneField(OrderLine, on_delete=models.PROTECT, related_name="reservation")
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name="reservations")
    base_qty = models.PositiveBigIntegerField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.ACTIVE)
    expires_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(base_qty__gt=0), name="reservation_qty_positive")]

    def clean(self):
        super().clean()
        if self.line_id and self.lot_id and self.line.offer.lot_id != self.lot_id:
            raise ValidationError({"lot": "La reserva debe usar el lote ofertado"})
        if self.line_id and self.base_qty != self.line.base_qty:
            raise ValidationError({"base_qty": "La reserva debe coincidir con la línea"})


class InventoryMovement(Timestamps):
    class Kind(models.TextChoices):
        INBOUND = "INBOUND"
        LOCAL_SALE = "LOCAL_SALE"
        WEB_SALE = "WEB_SALE"
        WASTE = "WASTE"
        ADJUSTMENT = "ADJUSTMENT"

    class State(models.TextChoices):
        DRAFT = "DRAFT"
        CONFIRMED = "CONFIRMED"
        CANCELLED = "CANCELLED"

    store = models.ForeignKey(Store, on_delete=models.PROTECT)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    order = models.OneToOneField(Order, null=True, blank=True, on_delete=models.PROTECT)
    correction_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField(unique=True)
    request_hash = models.CharField(max_length=64)

    def clean(self):
        super().clean()
        if self.actor_id and self.actor.store_id != self.store_id:
            raise ValidationError({"actor": "Responsable de otra bodega"})
        if self.kind in (self.Kind.WASTE, self.Kind.ADJUSTMENT) and not self.reason.strip():
            raise ValidationError({"reason": "La merma o ajuste requiere motivo"})
        if self.kind == self.Kind.WEB_SALE and not self.order_id:
            raise ValidationError({"order": "Venta web requiere pedido"})
        if self.order_id and self.order.store_id != self.store_id:
            raise ValidationError({"order": "Pedido de otra bodega"})


class MovementLine(Timestamps):
    movement = models.ForeignKey(InventoryMovement, on_delete=models.PROTECT, related_name="lines")
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    physical_delta = models.BigIntegerField()
    step_price_snapshot = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    snapshot = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["movement", "lot"], name="movementline_lot_unique"),
            models.CheckConstraint(condition=~Q(physical_delta=0), name="movementline_delta_nonzero"),
        ]

    def clean(self):
        super().clean()
        if self.movement_id and self.lot_id and self.lot.product.store_id != self.movement.store_id:
            raise ValidationError({"lot": "Lote de otra bodega"})
        if self.movement_id:
            inbound = self.movement.kind == InventoryMovement.Kind.INBOUND
            adjustment = self.movement.kind == InventoryMovement.Kind.ADJUSTMENT
            if not adjustment and ((inbound and self.physical_delta <= 0) or (not inbound and self.physical_delta >= 0)):
                raise ValidationError({"physical_delta": "Signo incompatible con movimiento"})


class PaymentAttempt(Timestamps):
    class State(models.TextChoices):
        CREATED = "CREATED"
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"
        CANCELLED = "CANCELLED"
        UNKNOWN = "UNKNOWN"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payment_attempts")
    provider = models.CharField(max_length=20, default="MERCADOPAGO_TEST")
    external_reference = models.CharField(max_length=150, unique=True, null=True, blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.CREATED)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="PEN")
    approved_at = models.DateTimeField(null=True, blank=True)
    provider_key = models.UUIDField(unique=True)
    response_summary = models.JSONField(default=dict)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive")]

    def clean(self):
        super().clean()
        if self.order_id and (self.amount != self.order.total or self.currency != self.order.currency):
            raise ValidationError("El intento no coincide con el importe y moneda del pedido")


class PaymentEvent(Timestamps):
    attempt = models.ForeignKey(PaymentAttempt, null=True, blank=True, on_delete=models.PROTECT)
    provider = models.CharField(max_length=30)
    external_event_id = models.CharField(max_length=150)
    resource_id = models.CharField(max_length=150)
    state = models.CharField(max_length=10, default="PENDING")
    payload_summary = models.JSONField(default=dict)
    error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "external_event_id"], name="payment_event_unique")]


class StorePricingPolicy(Timestamps):
    class Mode(models.TextChoices):
        REVIEW = "REVIEW"
        AUTOMATIC = "AUTOMATIC"

    store = models.ForeignKey(Store, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.REVIEW)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "version"], name="pricing_policy_version_unique"),
            models.UniqueConstraint(fields=["store"], condition=Q(ends_at__isnull=True), name="one_current_pricing_policy"),
            models.CheckConstraint(condition=Q(version__gt=0), name="pricing_policy_version_positive"),
        ]

    def clean(self):
        super().clean()
        if self.created_by_id and (self.created_by.role != User.Role.OWNER or self.created_by.store_id != self.store_id):
            raise ValidationError({"created_by": "Solo el dueño de la tienda fija política"})


class OfferLimit(Timestamps):
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    max_discount_pct = models.DecimalField(max_digits=5, decimal_places=2)
    minimum_price = models.DecimalField(max_digits=14, decimal_places=2)
    below_cost_authorized = models.BooleanField(default=False)
    authorized_by = models.ForeignKey(User, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["offer", "version"], name="offer_limit_version_unique"),
            models.UniqueConstraint(fields=["offer"], condition=Q(ends_at__isnull=True), name="one_current_offer_limit"),
            models.CheckConstraint(condition=Q(version__gt=0), name="offer_limit_version_positive"),
            models.CheckConstraint(condition=Q(max_discount_pct__gte=0, max_discount_pct__lt=100), name="discount_pct_range"),
            models.CheckConstraint(condition=Q(minimum_price__gt=0), name="minimum_price_positive"),
        ]

    def clean(self):
        super().clean()
        if self.offer_id and self.authorized_by_id and (self.authorized_by.role != User.Role.OWNER or self.authorized_by.store_id != self.offer.lot.product.store_id):
            raise ValidationError({"authorized_by": "Solo el dueño de la tienda autoriza límites"})


class MLModel(Timestamps):
    version = models.CharField(max_length=80, unique=True)
    artifact_path = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=20, default="EXPERIMENTAL")
    features_version = models.CharField(max_length=40)
    dataset_version = models.CharField(max_length=80)
    metrics = models.JSONField(default=dict)
    configuration = models.JSONField(default=dict)
    trained_at = models.DateTimeField()


class AnalysisRun(Timestamps):
    store = models.ForeignKey(Store, on_delete=models.PROTECT)
    model = models.ForeignKey(MLModel, null=True, blank=True, on_delete=models.PROTECT)
    origin = models.CharField(max_length=10)
    state = models.CharField(max_length=12, default="PENDING")
    target_date = models.DateField()
    deduplication_key = models.CharField(max_length=150, unique=True)
    error_code = models.CharField(max_length=80, blank=True)


class Recommendation(Timestamps):
    run = models.ForeignKey(AnalysisRun, on_delete=models.PROTECT)
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT)
    offer_version = models.PositiveIntegerField()
    policy_version = models.PositiveIntegerField()
    limit_version = models.PositiveIntegerField()
    current_price = models.DecimalField(max_digits=14, decimal_places=2)
    proposed_price = models.DecimalField(max_digits=14, decimal_places=2)
    snapshot = models.JSONField(default=dict)
    predictions = models.JSONField(default=dict)
    explanation = models.TextField()
    state = models.CharField(max_length=12)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "offer"], name="recommendation_run_offer_unique")]


class PriceChange(Timestamps):
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT)
    recommendation = models.OneToOneField(Recommendation, null=True, blank=True, on_delete=models.PROTECT)
    old_price = models.DecimalField(max_digits=14, decimal_places=2)
    new_price = models.DecimalField(max_digits=14, decimal_places=2)
    origin = models.CharField(max_length=10)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    reason = models.TextField()
    limit_version = models.PositiveIntegerField()
    model_version = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(new_price__gt=0, new_price__lte=F("old_price")), name="price_change_never_raise")]


class Job(Timestamps):
    kind = models.CharField(max_length=60)
    key = models.CharField(max_length=150, unique=True)
    payload = models.JSONField(default=dict)
    state = models.CharField(max_length=12, default="PENDING")
    available_at = models.DateTimeField()
    lease_until = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=80, blank=True)


class AuditEvent(Timestamps):
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    correlation_id = models.UUIDField()
