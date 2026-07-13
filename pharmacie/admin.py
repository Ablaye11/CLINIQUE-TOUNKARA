from django.contrib import admin
from .models import Fournisseur, Medicament, MouvementStock, Vente, LigneVente

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'email', 'created_at')
    search_fields = ('nom', 'telephone', 'email')

@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'categorie', 'stock', 'prix_achat', 'prix_vente', 'date_expiration', 'statut')
    list_filter = ('categorie', 'date_expiration')
    search_fields = ('code', 'nom', 'categorie')

@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ('medicament', 'type_mouvement', 'quantite', 'date_mouvement', 'motif')
    list_filter = ('type_mouvement', 'date_mouvement')
    search_fields = ('medicament__nom', 'motif')

class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0

@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ('numero_facture', 'date_vente', 'mode_paiement', 'total')
    list_filter = ('mode_paiement', 'date_vente')
    search_fields = ('numero_facture',)
    inlines = [LigneVenteInline]
