from django.db import models
from django.utils import timezone
from datetime import date

class Fournisseur(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom du fournisseur")
    telephone = models.CharField(max_length=20, verbose_name="Téléphone", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    adresse = models.TextField(verbose_name="Adresse", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    class Meta:
        ordering = ['nom']


class Medicament(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Code médicament / Code-barres")
    nom = models.CharField(max_length=150, verbose_name="Nom du médicament")
    categorie = models.CharField(max_length=100, verbose_name="Catégorie")
    stock = models.IntegerField(default=0, verbose_name="Stock disponible")
    stock_minimum = models.IntegerField(default=5, verbose_name="Stock minimum d'alerte")
    prix_achat = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Prix d'achat (FCFA)")
    prix_vente = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Prix de vente (FCFA)")
    date_expiration = models.DateField(verbose_name="Date d'expiration")
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Fournisseur")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def statut(self):
        aujourdhui = date.today()
        if self.date_expiration <= aujourdhui:
            return "Expiré"
        elif self.stock <= 0:
            return "Rupture"
        elif self.stock <= self.stock_minimum:
            return "Stock faible"
        else:
            return "Disponible"

    @property
    def jours_avant_expiration(self):
        aujourdhui = date.today()
        delta = self.date_expiration - aujourdhui
        return delta.days

    def __str__(self):
        return f"{self.nom} ({self.code})"

    class Meta:
        ordering = ['nom']


class MouvementStock(models.Model):
    TYPES_MOUVEMENT = [
        ('ENTREE', 'Entrée de stock'),
        ('SORTIE', 'Sortie de stock'),
        ('AJUSTEMENT', 'Ajustement d\'inventaire'),
    ]

    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE, related_name='mouvements', verbose_name="Médicament")
    type_mouvement = models.CharField(max_length=20, choices=TYPES_MOUVEMENT, verbose_name="Type de mouvement")
    quantite = models.IntegerField(verbose_name="Quantité")
    date_mouvement = models.DateTimeField(default=timezone.now, verbose_name="Date du mouvement")
    motif = models.CharField(max_length=255, blank=True, null=True, verbose_name="Motif / Commentaire")
    # ✅ NOUVEAU — traçabilité pharmaceutique obligatoire
    numero_lot = models.CharField(max_length=100, blank=True, null=True, verbose_name="Numéro de lot")

    def save(self, *args, **kwargs):
        # Mettre à jour le stock du médicament lors de la sauvegarde du mouvement
        is_new = self.pk is None
        if is_new:
            medicament = self.medicament
            if self.type_mouvement == 'ENTREE':
                medicament.stock += self.quantite
            elif self.type_mouvement == 'SORTIE':
                medicament.stock -= self.quantite
            elif self.type_mouvement == 'AJUSTEMENT':
                medicament.stock = self.quantite
            medicament.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type_mouvement} - {self.medicament.nom} ({self.quantite})"

    class Meta:
        ordering = ['-date_mouvement']


class Vente(models.Model):
    MODES_PAIEMENT = [
        ('ESPECES', 'Espèces'),
        ('OM', 'Orange Money'),
        ('WAVE', 'Wave'),
        ('CHEQUE', 'Chèque'),
        ('COMPTE', 'Compte Clinique'),
    ]

    numero_facture = models.CharField(max_length=50, unique=True, verbose_name="N° Facture")
    client_nom = models.CharField(max_length=150, default="Passant", verbose_name="Nom du client")
    client_adresse = models.TextField(blank=True, null=True, verbose_name="Adresse du client")
    client_age = models.CharField(max_length=50, blank=True, null=True, verbose_name="Âge du client")
    client_telephone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Téléphone du client")
    date_vente = models.DateTimeField(default=timezone.now, verbose_name="Date de vente")
    mode_paiement = models.CharField(max_length=20, choices=MODES_PAIEMENT, default='ESPECES', verbose_name="Mode de paiement")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total (FCFA)")
    # ✅ NOUVEAU — permet de marquer une vente comme annulée sans la supprimer
    est_annulee = models.BooleanField(default=False, verbose_name="Vente annulée")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Facture {self.numero_facture} - {self.total} FCFA"

    class Meta:
        ordering = ['-date_vente']


class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='lignes', verbose_name="Vente")
    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE, verbose_name="Médicament")
    quantite = models.IntegerField(verbose_name="Quantité")
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Prix unitaire (FCFA)")
    # ✅ NOUVEAU — remise en pourcentage (0 par défaut = pas de remise)
    remise = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Remise (%)")
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total (FCFA)")

    def save(self, *args, **kwargs):
        # ✅ CORRECTION BUG CRITIQUE — Calcul du total avec remise éventuelle
        # Le total tient compte de la remise : prix_unitaire * qté * (1 - remise/100)
        facteur_remise = 1 - (self.remise / 100)
        self.total = self.quantite * self.prix_unitaire * facteur_remise

        # ✅ CORRECTION BUG CRITIQUE — Ne plus décrémenter manuellement le stock ici.
        # La création du MouvementStock ci-dessous s'en charge via MouvementStock.save().
        # L'ancienne double déduction a été supprimée.
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Enregistrer uniquement le mouvement de sortie → c'est lui qui décrémente le stock
            MouvementStock.objects.create(
                medicament=self.medicament,
                type_mouvement='SORTIE',
                quantite=self.quantite,
                motif=f"Vente Facture N° {self.vente.numero_facture}"
            )

    def __str__(self):
        return f"{self.medicament.nom} x {self.quantite}"
