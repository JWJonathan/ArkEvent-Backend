from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    MarketplaceCategory, MarketplaceProvider, ProviderDocument,
    MarketplaceService, ServiceImage, ServicePackage,
    ServiceAvailability, ServiceFavorite, ServiceReview,
    ServiceBooking, BookingPayment, MarketplaceMessage
)

# --- Inlines ---

class ProviderDocumentInline(admin.TabularInline):
    model = ProviderDocument
    extra = 1
    readonly_fields = ('reviewed_at', 'reviewed_by')
    fields = ('document_type', 'file', 'status', 'reviewed_by', 'reviewed_at', 'notes')


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'sort_order')


class ServicePackageInline(admin.TabularInline):
    model = ServicePackage
    extra = 1
    fields = ('name', 'price', 'delivery_time_days', 'revisions', 'is_popular', 'is_active')


class ServiceAvailabilityInline(admin.TabularInline):
    model = ServiceAvailability
    extra = 3


class BookingPaymentInline(admin.TabularInline):
    model = BookingPayment
    extra = 0
    readonly_fields = ('paid_at', 'transaction_id')


# --- Admins ---

@admin.register(MarketplaceCategory)
class MarketplaceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'order', 'created_at')
    list_filter = ('is_active', 'parent')
    list_editable = ('is_active', 'order')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')


@admin.register(MarketplaceProvider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'city', 'verified', 'display_rating', 'is_active')
    list_filter = ('verified', 'is_active', 'city', 'country', 'provider_type')
    search_fields = ('business_name', 'user__email', 'city', 'registration_number')
    readonly_fields = ('average_rating', 'total_reviews', 'total_completed_jobs', 'total_sales')
    inlines = [ProviderDocumentInline]
    actions = ['verify_providers', 'deactivate_providers']

    def display_rating(self, obj):
        return format_html("<b>{}</b> / 5 ({} avis)", obj.average_rating, obj.total_reviews)
    display_rating.short_description = _("Note")

    @admin.action(description=_("Vérifier les prestataires sélectionnés"))
    def verify_providers(self, request, queryset):
        queryset.update(verified=True)
        self.message_user(request, _("Les prestataires sélectionnés ont été vérifiés."))

    @admin.action(description=_("Désactiver les prestataires sélectionnés"))
    def deactivate_providers(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, _("Les prestataires sélectionnés ont été désactivés."))


@admin.register(MarketplaceService)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'category', 'base_price', 'status', 'is_featured', 'bookings_count')
    list_filter = ('status', 'is_featured', 'service_type', 'category', 'city')
    search_fields = ('title', 'provider__business_name', 'city')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('provider', 'category')
    inlines = [ServiceImageInline, ServicePackageInline, ServiceAvailabilityInline]
    actions = ['publish_services', 'pause_services', 'feature_services']
    
    fieldsets = (
        (_("Général"), {
            'fields': ('provider', 'category', 'title', 'slug', 'service_type', 'status', 'is_featured')
        }),
        (_("Détails & Logistique"), {
            'fields': ('summary', 'description', 'amenities', 'min_guests', 'max_guests', 'preparation_time_days', 'instant_booking')
        }),
        (_("Tarification"), {
            'fields': ('currency', 'base_price', 'discount_price', 'price_unit')
        }),
        (_("Médias"), {
            'fields': ('featured_image', 'video_url')
        }),
        (_("Localisation"), {
            'fields': ('city', 'country')
        }),
        (_("Statistiques"), {
            'fields': ('views_count', 'reviews_count', 'average_rating', 'favorites_count', 'bookings_count'),
            'classes': ('collapse',)
        }),
        (_("SEO"), {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )

    @admin.action(description=_("Publier les services sélectionnés"))
    def publish_services(self, request, queryset):
        queryset.update(status=MarketplaceService.Status.PUBLISHED)
        self.message_user(request, _("Services publiés."))

    @admin.action(description=_("Mettre en pause les services sélectionnés"))
    def pause_services(self, request, queryset):
        queryset.update(status=MarketplaceService.Status.PAUSED)
        self.message_user(request, _("Services mis en pause."))

    @admin.action(description=_("Mettre en avant les services sélectionnés"))
    def feature_services(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, _("Services mis en avant."))


@admin.register(ServiceBooking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'service', 'customer', 'start_date', 'total_amount', 'status')
    list_filter = ('status', 'booking_date', 'start_date')
    search_fields = ('reference', 'customer__email', 'service__title', 'customer__first_name', 'customer__last_name')
    readonly_fields = ('reference', 'booking_date', 'total_amount', 'commission_amount')
    autocomplete_fields = ('service', 'customer', 'event', 'package')
    inlines = [BookingPaymentInline]
    date_hierarchy = 'start_date'
    actions = ['confirm_booking', 'complete_booking', 'cancel_booking']

    @admin.action(description=_("Confirmer les réservations"))
    def confirm_booking(self, request, queryset):
        queryset.update(status=ServiceBooking.BookingStatus.CONFIRMED)
        self.message_user(request, _("Réservations confirmées."))

    @admin.action(description=_("Marquer comme terminées"))
    def complete_booking(self, request, queryset):
        queryset.update(status=ServiceBooking.BookingStatus.COMPLETED)
        self.message_user(request, _("Réservations marquées comme terminées."))

    @admin.action(description=_("Annuler les réservations"))
    def cancel_booking(self, request, queryset):
        queryset.update(status=ServiceBooking.BookingStatus.CANCELLED)
        self.message_user(request, _("Réservations annulées."))


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'reviewer', 'rating', 'is_verified_purchase', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'created_at')
    search_fields = ('comment', 'service__title', 'reviewer__email')
    autocomplete_fields = ('service', 'reviewer', 'event_reference')


@admin.register(MarketplaceMessage)
class MarketplaceMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'booking', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('message', 'sender__email', 'receiver__email')
    autocomplete_fields = ('sender', 'receiver', 'booking')


@admin.register(ServiceFavorite)
class ServiceFavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'created_at')
    search_fields = ('user__email', 'service__title')
    autocomplete_fields = ('user', 'service')


@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'service__title')


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ('service', 'is_primary', 'sort_order')
    search_fields = ('service__title',)


@admin.register(ServiceAvailability)
class ServiceAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('service', 'date', 'is_available')
    list_filter = ('date', 'is_available')
    search_fields = ('service__title',)


@admin.register(ProviderDocument)
class ProviderDocumentAdmin(admin.ModelAdmin):
    list_display = ('provider', 'document_type', 'status', 'created_at')
    list_filter = ('status', 'document_type')
    search_fields = ('provider__business_name',)


@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'booking', 'amount', 'payment_status', 'paid_at')
    list_filter = ('payment_status', 'payment_method', 'paid_at')
    search_fields = ('transaction_id', 'booking__reference')
    autocomplete_fields = ('booking',)
