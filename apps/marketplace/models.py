import uuid
from django.db import models, transaction
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

# --- Mixins & Base Models ---

class TimeStampedModel(models.Model):
    """Modèle de base avec horodatage et UUID pour les identifiants."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Créé le"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Modifié le"))

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, verbose_name=_("Supprimé"))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Supprimé le"))

    class Meta:
        abstract = True

    def delete(self, **kwargs):
        self.is_deleted = True
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save()


class SEOModel(models.Model):
    """Champs SEO pour améliorer la visibilité sur les moteurs de recherche."""
    meta_title = models.CharField(max_length=70, blank=True, verbose_name=_("Meta Titre SEO"))
    meta_description = models.CharField(max_length=160, blank=True, verbose_name=_("Meta Description SEO"))

    class Meta:
        abstract = True


# --- Marketplace Models ---

class MarketplaceCategory(TimeStampedModel, SEOModel):
    """Catégories hiérarchiques pour organiser les services/produits."""
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='subcategories', verbose_name=_("Catégorie parente")
    )
    name = models.CharField(max_length=100, verbose_name=_("Nom"))
    slug = models.SlugField(max_length=120, unique=True, verbose_name=_("Slug"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    icon = models.CharField(max_length=50, blank=True, help_text=_("Ex: fa-music"), verbose_name=_("Icône"))
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Ordre d'affichage"))

    class Meta:
        verbose_name = _("Catégorie Marketplace")
        verbose_name_plural = _("Catégories Marketplace")
        ordering = ['order', 'name']
        indexes = [models.Index(fields=['slug', 'is_active'])]

    def __str__(self):
        return f"{self.parent.name} > {self.name}" if self.parent else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MarketplaceProvider(TimeStampedModel, SoftDeleteModel):
    """Modèle représentant les prestataires de services/produits sur la marketplace."""
    class ProviderType(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', _("Auto-entrepreneur / Freelance")
        COMPANY = 'COMPANY', _("Société / Agence")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marketplace_profile',
        verbose_name=_("Utilisateur")
    )
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices, default=ProviderType.COMPANY, verbose_name=_("Type de prestataire"))
    business_name = models.CharField(max_length=200, db_index=True, verbose_name=_("Nom commercial / Raison sociale"))
    registration_number = models.CharField(max_length=50, blank=True, verbose_name=_("SIRET / Numéro d'immatriculation"))
    vat_number = models.CharField(max_length=50, blank=True, verbose_name=_("Numéro de TVA"))
    
    description = models.TextField(verbose_name=_("Présentation détaillée"))
    short_bio = models.CharField(max_length=255, blank=True, verbose_name=_("Slogan / Bio courte"))
    
    # Contact
    phone = models.CharField(max_length=20, verbose_name=_("Téléphone"))
    whatsapp = models.CharField(max_length=20, blank=True, verbose_name=_("WhatsApp"))
    email = models.EmailField(verbose_name=_("Email professionnel"))
    website = models.URLField(blank=True, verbose_name=_("Site web"))
    social_links = models.JSONField(default=dict, blank=True, help_text=_("Format: {'instagram': 'url', 'linkedin': 'url'}"))
    
    # Médias
    logo = models.ImageField(upload_to='marketplace/providers/logos/', blank=True, verbose_name=_("Logo"))
    cover_image = models.ImageField(upload_to='marketplace/providers/covers/', blank=True, verbose_name=_("Image de couverture"))
    
    # Localisation
    address = models.CharField(max_length=255, verbose_name=_("Adresse"))
    city = models.CharField(max_length=100, db_index=True, verbose_name=_("Ville"))
    postal_code = models.CharField(max_length=20, verbose_name=_("Code postal"))
    country = models.CharField(max_length=100, default="Haïti", verbose_name=_("Pays"))
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Business Rules
    cancellation_policy = models.TextField(blank=True, verbose_name=_("Politique d'annulation"))
    working_hours = models.JSONField(default=dict, blank=True, verbose_name=_("Horaires d'ouverture"))
    
    # Stats & État
    verified = models.BooleanField(default=False, verbose_name=_("Vérifié"))
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, verbose_name=_("Note moyenne"))
    total_reviews = models.PositiveIntegerField(default=0, verbose_name=_("Total avis"))
    total_completed_jobs = models.PositiveIntegerField(default=0, verbose_name=_("Missions terminées"))
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name=_("Volume d'affaires"))
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Prestataire")
        verbose_name_plural = _("Prestataires")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business_name']),
            models.Index(fields=['city', 'verified']),
        ]

    def __str__(self):
        return self.business_name

    def update_rating(self):
        """Recalcule la note moyenne à partir des avis."""
        reviews = ServiceReview.objects.filter(service__provider=self)
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.average_rating = round(avg, 2)
            self.total_reviews = reviews.count()
            self.save(update_fields=['average_rating', 'total_reviews'])

    def get_total_services(self):
        return self.services.filter(is_deleted=False).count()


class ProviderDocument(TimeStampedModel):
    """Documents justificatifs pour la validation des prestataires."""
    class DocumentType(models.TextChoices):
        ID_CARD = 'ID', _("Carte d'identité")
        BUSINESS_REG = 'BR', _("Registre du commerce (KBIS)")
        TAX_ID = 'TAX', _("Identifiant fiscal (NIF/SIRET)")
        PERMIT = 'PERMIT', _("Permis / Licence spécifique")

    class Status(models.TextChoices):
        PENDING = 'PENDING', _("En attente")
        APPROVED = 'APPROVED', _("Approuvé")
        REJECTED = 'REJECTED', _("Rejeté")

    provider = models.ForeignKey(
        MarketplaceProvider, 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name=_("Prestataire")
    )
    document_type = models.CharField(max_length=10, choices=DocumentType.choices, verbose_name=_("Type de document"))
    file = models.FileField(upload_to='marketplace/providers/docs/', verbose_name=_("Fichier"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name=_("Statut"))
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='reviewed_documents'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name=_("Notes de révision"))

    class Meta:
        verbose_name = _("Document prestataire")
        verbose_name_plural = _("Documents prestataires")


class MarketplaceService(TimeStampedModel, SoftDeleteModel, SEOModel):
    """Modèle représentant les services/produits proposés sur la marketplace."""
    class ServiceType(models.TextChoices):
        SERVICE = 'SERVICE', _("Service (DJ, Photographe...)")
        PRODUCT = 'PRODUCT', _("Produit (Vente/Location matériel)")
        VENUE = 'VENUE', _("Lieu / Espace")

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _("Brouillon")
        PENDING = 'PENDING', _("En attente de validation")
        PUBLISHED = 'PUBLISHED', _("Publié")
        PAUSED = 'PAUSED', _("En pause")
        REJECTED = 'REJECTED', _("Refusé")

    provider = models.ForeignKey(
        MarketplaceProvider, 
        on_delete=models.CASCADE, 
        related_name='services',
        verbose_name=_("Prestataire")
    )
    category = models.ForeignKey(
        MarketplaceCategory, 
        on_delete=models.PROTECT, 
        related_name='services',
        verbose_name=_("Catégorie")
    )
    
    title = models.CharField(max_length=200, db_index=True, verbose_name=_("Titre de l'offre"))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("Slug"))
    service_type = models.CharField(max_length=20, choices=ServiceType.choices, verbose_name=_("Type de service"))
    
    summary = models.CharField(max_length=255, verbose_name=_("Résumé accrocheur"))
    description = models.TextField(verbose_name=_("Description complète"))
    amenities = ArrayField(models.CharField(max_length=100), blank=True, default=list, help_text=_("Liste des équipements/inclusions"), verbose_name=_("Équipements"))
    
    # Capacité
    min_guests = models.PositiveIntegerField(default=1, null=True, blank=True, verbose_name=_("Nombre min. de convives"))
    max_guests = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Nombre max. de convives"))
    
    # Logistique
    preparation_time_days = models.PositiveIntegerField(default=0, verbose_name=_("Temps de préparation (jours)"))
    instant_booking = models.BooleanField(default=False, verbose_name=_("Réservation instantanée"))
    
    # Prix
    currency = models.CharField(max_length=3, default='USD', verbose_name=_("Devise"))
    base_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Prix de base"))
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_("Prix réduit"))
    price_unit = models.CharField(max_length=50, default=_("par événement"), help_text=_("ex: /heure, /jour, /personne"), verbose_name=_("Unité de prix"))
    
    # Localisation
    city = models.CharField(max_length=100, verbose_name=_("Ville"))
    country = models.CharField(max_length=100, default="France", verbose_name=_("Pays"))
    
    # Médias
    featured_image = models.ImageField(upload_to='marketplace/services/featured/', verbose_name=_("Image principale"))
    video_url = models.URLField(blank=True, help_text=_("Lien YouTube/Vimeo"), verbose_name=_("URL Vidéo"))
    
    # Stats
    views_count = models.PositiveIntegerField(default=0, verbose_name=_("Vues"))
    favorites_count = models.PositiveIntegerField(default=0, verbose_name=_("Favoris"))
    bookings_count = models.PositiveIntegerField(default=0, verbose_name=_("Réservations"))
    
    # État
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name=_("Statut"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Mis en avant"))

    class Meta:
        verbose_name = _("Service/Produit")
        verbose_name_plural = _("Services/Produits")
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['status', 'service_type', 'base_price']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return f"{self.title} - {self.provider.business_name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) + "-" + str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])

    def get_effective_price(self):
        return self.discount_price if self.discount_price else self.base_price


class ServiceImage(TimeStampedModel):
    service = models.ForeignKey(MarketplaceService, on_delete=models.CASCADE, related_name='images', verbose_name=_("Service"))
    image = models.ImageField(upload_to='marketplace/services/gallery/', verbose_name=_("Image"))
    alt_text = models.CharField(max_length=200, blank=True, verbose_name=_("Texte alternatif"))
    is_primary = models.BooleanField(default=False, verbose_name=_("Image principale"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Ordre de tri"))

    class Meta:
        verbose_name = _("Image de service")
        verbose_name_plural = _("Galerie d'images")
        ordering = ['sort_order']


class ServicePackage(TimeStampedModel):
    service = models.ForeignKey(MarketplaceService, on_delete=models.CASCADE, related_name='packages', verbose_name=_("Service"))
    name = models.CharField(max_length=100, verbose_name=_("Nom du pack"))
    description = models.TextField(verbose_name=_("Description"))
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Prix"))
    features = models.JSONField(default=list, blank=True, help_text=_("Liste des avantages inclus"), verbose_name=_("Inclusions"))
    delivery_time_days = models.PositiveIntegerField(default=1, verbose_name=_("Délai (jours)"))
    revisions = models.PositiveIntegerField(default=0, verbose_name=_("Révisions"))
    is_popular = models.BooleanField(default=False, verbose_name=_("Populaire"))
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Package tarifaire")
        verbose_name_plural = _("Packages tarifaires")


class ServiceAvailability(TimeStampedModel):
    service = models.ForeignKey(MarketplaceService, on_delete=models.CASCADE, related_name='availabilities', verbose_name=_("Service"))
    date = models.DateField(verbose_name=_("Date"))
    start_time = models.TimeField(null=True, blank=True, verbose_name=_("Heure de début"))
    end_time = models.TimeField(null=True, blank=True, verbose_name=_("Heure de fin"))
    is_available = models.BooleanField(default=True, verbose_name=_("Disponible"))

    class Meta:
        verbose_name = _("Disponibilité")
        verbose_name_plural = _("Disponibilités")
        constraints = [
            models.UniqueConstraint(fields=['service', 'date', 'start_time'], name='unique_service_availability')
        ]


class ServiceFavorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_services', verbose_name=_("Utilisateur"))
    service = models.ForeignKey(MarketplaceService, on_delete=models.CASCADE, related_name='favorited_by', verbose_name=_("Service"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ajouté le"))

    class Meta:
        verbose_name = _("Favori")
        verbose_name_plural = _("Favoris")
        constraints = [
            models.UniqueConstraint(fields=['user', 'service'], name='unique_user_favorite_service')
        ]


class ServiceReview(TimeStampedModel):
    service = models.ForeignKey(MarketplaceService, on_delete=models.CASCADE, related_name='reviews', verbose_name=_("Service"))
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='market_reviews', verbose_name=_("Auteur"))
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Note")
    )
    title = models.CharField(max_length=200, blank=True, verbose_name=_("Titre"))
    comment = models.TextField(verbose_name=_("Commentaire"))
    is_verified_purchase = models.BooleanField(default=False, verbose_name=_("Achat vérifié"))
    reply_from_provider = models.TextField(blank=True, verbose_name=_("Réponse du prestataire"))
    
    # Référence optionnelle vers un événement ArkEvent
    event_reference = models.ForeignKey(
        'events.Event', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='marketplace_reviews',
        verbose_name=_("Événement associé")
    )

    class Meta:
        verbose_name = _("Avis client")
        verbose_name_plural = _("Avis clients")
        ordering = ['-created_at']
        unique_together = ('service', 'reviewer')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.service.provider.update_rating()


class ServiceBooking(TimeStampedModel):
    class BookingStatus(models.TextChoices):
        PENDING = 'PENDING', _("En attente")
        AWAITING_PAYMENT = 'AWAITING_PAYMENT', _("En attente de paiement")
        CONFIRMED = 'CONFIRMED', _("Confirmée")
        IN_PROGRESS = 'IN_PROGRESS', _("En cours")
        COMPLETED = 'COMPLETED', _("Terminée")
        CANCELLED = 'CANCELLED', _("Annulée")
        REFUNDED = 'REFUNDED', _("Remboursée")

    reference = models.CharField(max_length=20, unique=True, editable=False, verbose_name=_("Référence"))
    service = models.ForeignKey(MarketplaceService, on_delete=models.PROTECT, related_name='bookings', verbose_name=_("Service"))
    package = models.ForeignKey(ServicePackage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Pack choisi"))
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='marketplace_bookings', verbose_name=_("Client"))
    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_bookings', verbose_name=_("Événement ArkEvent"))
    
    # Dates
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de réservation"))
    start_date = models.DateTimeField(verbose_name=_("Date/Heure de début"))
    end_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Date/Heure de fin"))
    
    # Financier
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant total"))
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name=_("Acompte payé"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name=_("Commission plateforme"))
    
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING, verbose_name=_("Statut"))
    customer_notes = models.TextField(blank=True, verbose_name=_("Notes client"))
    provider_notes = models.TextField(blank=True, verbose_name=_("Notes prestataire"))

    class Meta:
        verbose_name = _("Réservation")
        verbose_name_plural = _("Réservations")
        ordering = ['-created_at']

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"ARK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class BookingPayment(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _("En attente")
        SUCCESS = 'SUCCESS', _("Réussi")
        FAILED = 'FAILED', _("Échoué")
        REFUNDED = 'REFUNDED', _("Remboursé")

    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='payments', verbose_name=_("Réservation"))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant"))
    payment_method = models.CharField(max_length=50, verbose_name=_("Méthode de paiement"))
    transaction_id = models.CharField(max_length=255, unique=True, verbose_name=_("ID Transaction"))
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, verbose_name=_("Statut"))
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Payé le"))

    class Meta:
        verbose_name = _("Paiement Marketplace")
        verbose_name_plural = _("Paiements Marketplace")


class MarketplaceMessage(TimeStampedModel):
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='messages', null=True, blank=True, verbose_name=_("Réservation"))
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_market_messages', verbose_name=_("Expéditeur"))
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_market_messages', verbose_name=_("Destinataire"))
    message = models.TextField(verbose_name=_("Message"))
    attachment = models.FileField(upload_to='marketplace/messages/', blank=True, null=True, verbose_name=_("Pièce jointe"))
    is_read = models.BooleanField(default=False, verbose_name=_("Lu"))

    class Meta:
        verbose_name = _("Message Marketplace")
        verbose_name_plural = _("Messages Marketplace")
        ordering = ['created_at']
