from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Sum, F, Q, Count
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from datetime import date, timedelta
import json
from decimal import Decimal, InvalidOperation
import csv
import io

from .models import Fournisseur, Medicament, MouvementStock, Vente, LigneVente

# ============================================================
# AUTHENTICATION VIEWS
# ============================================================

def get_user_role(user):
    """Returns the role of a Django user based on profile data."""
    if user.is_superuser:
        return 'superadmin'
    # Role stored in last_name field (lightweight approach, no extra model needed)
    if user.last_name == 'caissier':
        return 'caissier'
    return 'admin'

def role_required(*roles):
    """Decorator that allows only users with specified roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/login/')
            user_role = get_user_role(request.user)
            if user_role not in roles:
                # Caissier trying to access admin pages
                return redirect('gestion_ventes')
            return view_func(request, *args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator

def api_role_required(*roles):
    """Decorator for API views that returns JSON error instead of redirecting."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Non authentifié'}, status=401)
            user_role = get_user_role(request.user)
            if user_role not in roles:
                return JsonResponse({'error': 'Accès refusé'}, status=403)
            return view_func(request, *args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator

def login_view(request):
    if request.user.is_authenticated:
        role = get_user_role(request.user)
        if role == 'caissier':
            return redirect('gestion_ventes')
        return redirect('dashboard')
    error = None
    username = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                role = get_user_role(user)
                if role == 'caissier':
                    return redirect('gestion_ventes')
                return redirect('dashboard')
            else:
                error = 'Ce compte est désactivé.'
        else:
            error = 'Identifiant ou mot de passe incorrect.'
    return render(request, 'pharmacie/login.html', {'error': error, 'username': username})

def logout_view(request):
    logout(request)
    return redirect('/login/')

# ============================================================
# PAGE VIEWS (with login & role protection)
# ============================================================

@login_required(login_url='/login/')
@role_required('superadmin', 'admin')
def dashboard(request):
    return render(request, 'pharmacie/dashboard.html')

@login_required(login_url='/login/')
@role_required('superadmin', 'admin')
def liste_medicaments(request):
    fournisseurs = Fournisseur.objects.all()
    categories = Medicament.objects.values_list('categorie', flat=True).distinct()
    return render(request, 'pharmacie/medicaments.html', {
        'fournisseurs': fournisseurs,
        'categories': categories
    })

@login_required(login_url='/login/')
@role_required('superadmin', 'admin')
def gestion_stocks(request):
    medicaments = Medicament.objects.all()
    return render(request, 'pharmacie/stocks.html', {'medicaments': medicaments})

@login_required(login_url='/login/')
@role_required('superadmin', 'admin')
def alertes_page(request):
    return render(request, 'pharmacie/alertes.html')

@login_required(login_url='/login/')
@role_required('superadmin', 'admin', 'caissier')
def gestion_ventes(request):
    return render(request, 'pharmacie/ventes.html')

@login_required(login_url='/login/')
@role_required('superadmin', 'admin')
def gestion_fournisseurs(request):
    return render(request, 'pharmacie/fournisseurs.html')

@login_required(login_url='/login/')
@role_required('superadmin', 'admin')
def rapports_page(request):
    return render(request, 'pharmacie/rapports.html')

@login_required(login_url='/login/')
@role_required('superadmin')
def utilisateurs_page(request):
    return render(request, 'pharmacie/utilisateurs.html')


# --- API ENDPOINTS (JSON pour le frontend dynamique) ---

@api_role_required('superadmin', 'admin')
def api_dashboard_stats(request):
    aujourdhui = date.today()
    demain = aujourdhui + timedelta(days=1)
    trente_jours = aujourdhui + timedelta(days=30)
    
    # 1. Valeur totale du stock (prix d'achat & prix de vente)
    medicaments = Medicament.objects.all()
    valeur_achat = sum(m.stock * m.prix_achat for m in medicaments)
    valeur_vente = sum(m.stock * m.prix_vente for m in medicaments)
    
    # 2. Nombre total de médicaments différents
    nb_medicaments = medicaments.count()
    
    # 3. Produits en rupture
    ruptures = medicaments.filter(stock__lte=0).count()
    
    # 4. Produits proches de l'expiration (< 30 jours ou déjà expirés)
    expirations_proches = medicaments.filter(date_expiration__lte=trente_jours).count()
    
    # 5. Ventes du jour (hors ventes annulées)
    ventes_du_jour = Vente.objects.filter(
        date_vente__range=(aujourdhui, demain),
        est_annulee=False
    ).aggregate(total_ventes=Sum('total'))['total_ventes'] or 0
    
    # 6. Achats du jour (estimé via les entrées de stock du jour)
    mouvements_entrees = MouvementStock.objects.filter(type_mouvement='ENTREE', date_mouvement__date=aujourdhui)
    achats_du_jour = sum(mouv.quantite * mouv.medicament.prix_achat for mouv in mouvements_entrees)
    
    # 7. Données pour graphiques (ventes des 7 derniers jours)
    graph_jours = []
    graph_ventes = []
    graph_benefices = []
    
    for i in range(6, -1, -1):
        jour_cible = aujourdhui - timedelta(days=i)
        jour_nom = jour_cible.strftime('%a %d')
        ventes_jour = Vente.objects.filter(date_vente__date=jour_cible, est_annulee=False)
        total_jour = ventes_jour.aggregate(total=Sum('total'))['total'] or 0
        
        # Calculer le bénéfice sur les ventes du jour
        lignes = LigneVente.objects.filter(vente__in=ventes_jour)
        benefice_jour = 0
        for lig in lignes:
            benefice_jour += (lig.prix_unitaire - lig.medicament.prix_achat) * lig.quantite
            
        graph_jours.append(jour_nom)
        graph_ventes.append(float(total_jour))
        graph_benefices.append(float(benefice_jour))
        
    return JsonResponse({
        'valeur_stock_achat': float(valeur_achat),
        'valeur_stock_vente': float(valeur_vente),
        'nb_medicaments': nb_medicaments,
        'ruptures': ruptures,
        'expirations_proches': expirations_proches,
        'ventes_du_jour': float(ventes_du_jour),
        'achats_du_jour': float(achats_du_jour),
        'graph': {
            'labels': graph_jours,
            'ventes': graph_ventes,
            'benefices': graph_benefices
        }
    })

@api_role_required('superadmin', 'admin', 'caissier')
def api_medicaments_liste(request):
    query = request.GET.get('q', '')
    cat = request.GET.get('categorie', '')
    statut_filter = request.GET.get('statut', '')
    exp_filter = request.GET.get('exp', '') # 'proche' (30j) ou 'expired'

    aujourdhui = date.today()
    meds = Medicament.objects.all()

    if query:
        meds = meds.filter(Q(nom__icontains=query) | Q(code__icontains=query) | Q(categorie__icontains=query))
    if cat:
        meds = meds.filter(categorie=cat)
        
    # Filtrer par statut
    data = []
    for m in meds:
        statut = m.statut
        if statut_filter and statut.lower() != statut_filter.lower():
            continue
            
        # Check expiration filter
        if exp_filter == 'expired' and m.date_expiration > aujourdhui:
            continue
        elif exp_filter == 'proche':
            trente_jours = aujourdhui + timedelta(days=30)
            if m.date_expiration <= aujourdhui or m.date_expiration > trente_jours:
                continue
        elif exp_filter == '60':
            soixante_jours = aujourdhui + timedelta(days=60)
            if m.date_expiration <= aujourdhui or m.date_expiration > soixante_jours:
                continue
        elif exp_filter == '90':
            quatre_vingt_dix_jours = aujourdhui + timedelta(days=90)
            if m.date_expiration <= aujourdhui or m.date_expiration > quatre_vingt_dix_jours:
                continue

        data.append({
            'id': m.id,
            'code': m.code,
            'nom': m.nom,
            'categorie': m.categorie,
            'stock': m.stock,
            'stock_minimum': m.stock_minimum,
            'prix_achat': float(m.prix_achat),
            'prix_vente': float(m.prix_vente),
            'date_expiration': m.date_expiration.isoformat(),
            'jours_avant_expiration': m.jours_avant_expiration,
            'fournisseur_id': m.fournisseur.id if m.fournisseur else '',
            'fournisseur_nom': m.fournisseur.nom if m.fournisseur else 'Aucun',
            'statut': statut
        })

    sort_by = request.GET.get('sort', 'nom')
    reverse = request.GET.get('reverse', 'false') == 'true'
    
    if sort_by in ['nom', 'stock', 'prix_vente', 'date_expiration']:
        data.sort(key=lambda x: x[sort_by], reverse=reverse)
        
    return JsonResponse({'medicaments': data})

@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_medicament_save(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            med_id = data.get('id')
            
            prix_achat = Decimal(str(data.get('prix_achat', 0)))
            prix_vente = Decimal(str(data.get('prix_vente', 0)))
            stock = int(data.get('stock', 0))
            stock_min = int(data.get('stock_minimum', 5))
            
            fournisseur_id = data.get('fournisseur')
            fournisseur = None
            if fournisseur_id:
                fournisseur = Fournisseur.objects.filter(id=fournisseur_id).first()

            if med_id:
                med = get_object_or_404(Medicament, id=med_id)
                old_stock = med.stock
                med.code = data.get('code')
                med.nom = data.get('nom')
                med.categorie = data.get('categorie')
                med.prix_achat = prix_achat
                med.prix_vente = prix_vente
                med.stock_minimum = stock_min
                med.date_expiration = data.get('date_expiration')
                med.fournisseur = fournisseur
                
                if old_stock != stock:
                    med.stock = stock
                    med.save()
                    MouvementStock.objects.create(
                        medicament=med,
                        type_mouvement='AJUSTEMENT',
                        quantite=stock,
                        motif="Ajustement manuel lors de la modification rapide"
                    )
                else:
                    med.save()
            else:
                med = Medicament.objects.create(
                    code=data.get('code'),
                    nom=data.get('nom'),
                    categorie=data.get('categorie'),
                    stock=stock,
                    stock_minimum=stock_min,
                    prix_achat=prix_achat,
                    prix_vente=prix_vente,
                    date_expiration=data.get('date_expiration'),
                    fournisseur=fournisseur
                )
                if stock > 0:
                    MouvementStock.objects.create(
                        medicament=med,
                        type_mouvement='ENTREE',
                        quantite=stock,
                        motif="Entrée initiale de stock"
                    )

            return JsonResponse({'success': True, 'id': med.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_medicament_delete(request, med_id):
    if request.method == 'POST':
        med = get_object_or_404(Medicament, id=med_id)
        med.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# --- API STOCKS ---

@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_stock_mouvement(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            med_id = data.get('medicament')
            type_mouv = data.get('type_mouvement')
            qty = int(data.get('quantite', 0))
            motif = data.get('motif', '')
            numero_lot = data.get('numero_lot', '')  # ✅ NOUVEAU — numéro de lot

            med = get_object_or_404(Medicament, id=med_id)
            
            if type_mouv == 'SORTIE' and med.stock < qty:
                return JsonResponse({'success': False, 'error': 'Stock insuffisant'}, status=400)

            MouvementStock.objects.create(
                medicament=med,
                type_mouvement=type_mouv,
                quantite=qty,
                motif=motif,
                numero_lot=numero_lot or None
            )
            # ✅ FIX CRITIQUE — Rafraîchir depuis la base après que MouvementStock.save() a modifié le stock
            med.refresh_from_db()
            return JsonResponse({'success': True, 'new_stock': med.stock})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=405)

@api_role_required('superadmin', 'admin')
def api_stock_historique(request):
    mouvements = MouvementStock.objects.all().select_related('medicament')
    data = [{
        'id': m.id,
        'medicament_nom': m.medicament.nom,
        'medicament_code': m.medicament.code,
        'type_mouvement': m.type_mouvement,
        'quantite': m.quantite,
        'date_mouvement': m.date_mouvement.strftime('%d/%m/%Y %H:%M'),
        'motif': m.motif or '-',
        'numero_lot': m.numero_lot or '-',  # ✅ NOUVEAU
    } for m in mouvements]
    return JsonResponse({'historique': data})


# --- API FOURNISSEURS ---

@api_role_required('superadmin', 'admin')
def api_fournisseurs_liste(request):
    if request.method == 'GET':
        fournisseurs = Fournisseur.objects.all().annotate(
            nb_produits=Count('medicament')
        )
        data = [{
            'id': f.id,
            'nom': f.nom,
            'telephone': f.telephone or '-',
            'email': f.email or '-',
            'adresse': f.adresse or '-',
            'nb_produits': f.nb_produits
        } for f in fournisseurs]
        return JsonResponse({'fournisseurs': data})
        
@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_fournisseur_save(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            f_id = data.get('id')
            if f_id:
                fourn = get_object_or_404(Fournisseur, id=f_id)
                fourn.nom = data.get('nom')
                fourn.telephone = data.get('telephone')
                fourn.email = data.get('email')
                fourn.adresse = data.get('adresse')
                fourn.save()
            else:
                fourn = Fournisseur.objects.create(
                    nom=data.get('nom'),
                    telephone=data.get('telephone'),
                    email=data.get('email'),
                    adresse=data.get('adresse')
                )
            return JsonResponse({'success': True, 'id': fourn.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_fournisseur_delete(request, f_id):
    if request.method == 'POST':
        fourn = get_object_or_404(Fournisseur, id=f_id)
        fourn.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# --- API VENTES & POS ---

@csrf_exempt
@transaction.atomic
@api_role_required('superadmin', 'admin', 'caissier')
def api_vente_creer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lignes_data = data.get('lignes', [])
            mode_paiement = data.get('mode_paiement', 'ESPECES')
            client_nom = data.get('client_nom', 'Passant')
            client_adresse = data.get('client_adresse', '')
            client_age_raw = data.get('client_age')
            client_telephone = data.get('client_telephone', '')
            
            client_age = None
            if client_age_raw is not None and str(client_age_raw).strip() != '':
                client_age = str(client_age_raw).strip()
            
            if not lignes_data:
                return JsonResponse({'success': False, 'error': 'Le panier est vide'}, status=400)

            # ✅ Vérification des stocks avec SELECT FOR UPDATE (lock pour éviter race conditions)
            for items in lignes_data:
                med = Medicament.objects.select_for_update().get(id=items['medicament_id'])
                qty = int(items['quantite'])
                if med.stock < qty:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Stock insuffisant pour {med.nom} (Disponible: {med.stock})'
                    }, status=400)

            # Créer le numéro de facture unique
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            last_id = Vente.objects.all().order_by('-id').first()
            seq = (last_id.id + 1) if last_id else 1
            num_facture = f"FAC-{timestamp}-{seq}"
            
            # Créer la vente
            vente = Vente.objects.create(
                numero_facture=num_facture,
                client_nom=client_nom,
                client_adresse=client_adresse,
                client_age=client_age,
                client_telephone=client_telephone,
                mode_paiement=mode_paiement,
                total=0
            )
            
            total_vente = Decimal('0.0')
            for items in lignes_data:
                med = Medicament.objects.get(id=items['medicament_id'])
                qty = int(items['quantite'])
                prix = Decimal(str(items['prix_vente']))
                # ✅ NOUVEAU — Remise optionnelle par ligne
                remise = Decimal(str(items.get('remise', 0)))
                
                ligne = LigneVente.objects.create(
                    vente=vente,
                    medicament=med,
                    quantite=qty,
                    prix_unitaire=prix,
                    remise=remise,
                    # total est calculé automatiquement dans LigneVente.save()
                    total=0
                )
                total_vente += ligne.total
                
            vente.total = total_vente
            vente.save()
            
            return JsonResponse({
                'success': True,
                'numero_facture': num_facture,
                'vente_id': vente.id,
                'total': float(total_vente)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
    return JsonResponse({'success': False}, status=405)


# ✅ NOUVEAU — Annulation d'une vente avec restitution du stock
@csrf_exempt
@transaction.atomic
@api_role_required('superadmin', 'admin')
def api_vente_annuler(request, vente_id):
    if request.method == 'POST':
        try:
            vente = get_object_or_404(Vente, id=vente_id)
            
            if vente.est_annulee:
                return JsonResponse({'success': False, 'error': 'Cette vente est déjà annulée'}, status=400)
            
            # Restituer le stock pour chaque ligne de vente
            for ligne in vente.lignes.all():
                MouvementStock.objects.create(
                    medicament=ligne.medicament,
                    type_mouvement='ENTREE',
                    quantite=ligne.quantite,
                    motif=f"Annulation Facture N° {vente.numero_facture}"
                )
            
            # Marquer la vente comme annulée (on ne supprime pas pour garder la traçabilité)
            vente.est_annulee = True
            vente.save()
            
            return JsonResponse({'success': True, 'message': f'Vente {vente.numero_facture} annulée. Stock restitué.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Méthode invalide'}, status=405)


@api_role_required('superadmin', 'admin', 'caissier')
def api_ventes_historique(request):
    # ✅ AMÉLIORATION — Filtre optionnel par période
    periode = request.GET.get('periode', 'tout')
    aujourdhui = date.today()
    
    ventes_qs = Vente.objects.all().prefetch_related('lignes__medicament')
    
    if periode == 'jour':
        ventes_qs = ventes_qs.filter(date_vente__date=aujourdhui)
    elif periode == 'semaine':
        ventes_qs = ventes_qs.filter(date_vente__date__gte=aujourdhui - timedelta(days=7))
    elif periode == 'mois':
        ventes_qs = ventes_qs.filter(date_vente__date__gte=aujourdhui - timedelta(days=30))
    elif periode == 'an':
        ventes_qs = ventes_qs.filter(date_vente__date__gte=aujourdhui - timedelta(days=365))
    
    data = []
    for v in ventes_qs:
        lignes = [{
            'medicament_nom': l.medicament.nom,
            'quantite': l.quantite,
            'prix_unitaire': float(l.prix_unitaire),
            'remise': float(l.remise),
            'total': float(l.total)
        } for l in v.lignes.all()]
        
        data.append({
            'id': v.id,
            'numero_facture': v.numero_facture,
            'client_nom': v.client_nom,
            'client_adresse': v.client_adresse or '-',
            'client_age': v.client_age or '-',
            'client_telephone': v.client_telephone or '-',
            'date_vente': v.date_vente.strftime('%d/%m/%Y %H:%M'),
            'mode_paiement': v.get_mode_paiement_display(),
            'total': float(v.total),
            'est_annulee': v.est_annulee,
            'lignes': lignes
        })
    return JsonResponse({'ventes': data})


@login_required(login_url='/login/')
@role_required('superadmin', 'admin', 'caissier')
def api_facture_pdf(request, vente_id):
    vente = get_object_or_404(Vente, id=vente_id)
    return render(request, 'pharmacie/facture_print.html', {'vente': vente})

@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_peupler_db(request):
    if request.method == 'POST':
        try:
            f, _ = Fournisseur.objects.get_or_create(
                nom="Pharmacie Nationale d'Approvisionnement (PNA)",
                defaults={
                    'telephone': "+221 33 821 00 00",
                    'email': "contact@pna.sn",
                    'adresse': "Dakar, Sénégal"
                }
            )
            
            aujourdhui = date.today()
            
            produits = [
                {'code': '3011234567890', 'nom': 'Doliprane 1000mg (Paracétamol)', 'categorie': 'Analgésique', 'stock': 150, 'stock_minimum': 10, 'prix_achat': 500.0, 'prix_vente': 750.0, 'date_expiration': aujourdhui + timedelta(days=730), 'fournisseur': f},
                {'code': '3011234567891', 'nom': 'Paracétamol Mylan 500mg', 'categorie': 'Analgésique', 'stock': 8, 'stock_minimum': 10, 'prix_achat': 300.0, 'prix_vente': 450.0, 'date_expiration': aujourdhui + timedelta(days=365), 'fournisseur': f},
                {'code': '3011234567892', 'nom': 'Amoxicilline Sandoz 500mg', 'categorie': 'Antibiotique', 'stock': 40, 'stock_minimum': 5, 'prix_achat': 1200.0, 'prix_vente': 1800.0, 'date_expiration': aujourdhui + timedelta(days=20), 'fournisseur': f},
                {'code': '3011234567893', 'nom': 'Ibuprofène Biogaran 400mg', 'categorie': 'Anti-inflammatoire', 'stock': 0, 'stock_minimum': 10, 'prix_achat': 400.0, 'prix_vente': 600.0, 'date_expiration': aujourdhui + timedelta(days=180), 'fournisseur': f},
                {'code': '3011234567894', 'nom': 'Spasfon Lyoc (Phloroglucinol)', 'categorie': 'Antispasmodique', 'stock': 60, 'stock_minimum': 5, 'prix_achat': 800.0, 'prix_vente': 1200.0, 'date_expiration': aujourdhui - timedelta(days=5), 'fournisseur': f},
                {'code': '3011234567895', 'nom': 'Gaviscon Suspension Buvable', 'categorie': 'Anti-acide', 'stock': 25, 'stock_minimum': 5, 'prix_achat': 900.0, 'prix_vente': 1400.0, 'date_expiration': aujourdhui + timedelta(days=450), 'fournisseur': f},
                {'code': '3011234567896', 'nom': 'Augmentin Nourrisson 100mg', 'categorie': 'Antibiotique', 'stock': 15, 'stock_minimum': 3, 'prix_achat': 2200.0, 'prix_vente': 3100.0, 'date_expiration': aujourdhui + timedelta(days=95), 'fournisseur': f},
                {'code': '3011234567897', 'nom': 'Ventoline HFA Inhalateur', 'categorie': 'Bronchodilatateur', 'stock': 35, 'stock_minimum': 5, 'prix_achat': 1500.0, 'prix_vente': 2300.0, 'date_expiration': aujourdhui + timedelta(days=540), 'fournisseur': f},
            ]
            
            inserted = 0
            for prod in produits:
                med, created = Medicament.objects.get_or_create(
                    code=prod['code'],
                    defaults={
                        'nom': prod['nom'], 'categorie': prod['categorie'],
                        'stock': prod['stock'], 'stock_minimum': prod['stock_minimum'],
                        'prix_achat': Decimal(str(prod['prix_achat'])),
                        'prix_vente': Decimal(str(prod['prix_vente'])),
                        'date_expiration': prod['date_expiration'],
                        'fournisseur': prod['fournisseur']
                    }
                )
                if created:
                    inserted += 1
                    if med.stock > 0:
                        MouvementStock.objects.create(
                            medicament=med, type_mouvement='ENTREE',
                            quantite=med.stock, motif="Importation de stock initiale"
                        )
                        
            return JsonResponse({'success': True, 'inserted': inserted})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=405)


# --- API RAPPORTS DÉTAILLÉS ---

@api_role_required('superadmin', 'admin')
def api_rapports_data(request):
    periode = request.GET.get('periode', 'mois')
    aujourdhui = date.today()
    
    if periode == 'jour':
        start_date = aujourdhui
    elif periode == 'semaine':
        start_date = aujourdhui - timedelta(days=7)
    elif periode == 'an':
        start_date = aujourdhui - timedelta(days=365)
    else:
        start_date = aujourdhui - timedelta(days=30)
        
    # ✅ Exclure les ventes annulées des rapports
    ventes = Vente.objects.filter(date_vente__date__gte=start_date, est_annulee=False)
    
    total_ventes = ventes.aggregate(total=Sum('total'))['total'] or 0
    
    lignes = LigneVente.objects.filter(vente__in=ventes).select_related('medicament')
    total_benefice = 0
    for l in lignes:
        total_benefice += (l.prix_unitaire - l.medicament.prix_achat) * l.quantite
        
    top_meds_query = LigneVente.objects.filter(vente__in=ventes)\
        .values('medicament__nom')\
        .annotate(total_quantite=Sum('quantite'), total_somme=Sum('total'))\
        .order_by('-total_quantite')[:10]
        
    top_meds = [{
        'nom': item['medicament__nom'],
        'quantite': item['total_quantite'],
        'total': float(item['total_somme'])
    } for item in top_meds_query]
    
    cat_query = LigneVente.objects.filter(vente__in=ventes)\
        .values('medicament__categorie')\
        .annotate(total_quantite=Sum('quantite'))\
        .order_by('-total_quantite')
        
    categories_ventes = [{
        'categorie': item['medicament__categorie'],
        'quantite': item['total_quantite']
    } for item in cat_query]
    
    return JsonResponse({
        'periode': periode,
        'total_ventes': float(total_ventes),
        'total_benefice': float(total_benefice),
        'top_medicaments': top_meds,
        'categories_ventes': categories_ventes
    })


# --- IMPORT CSV ---

@api_role_required('superadmin', 'admin')
def api_import_template(request):
    """Télécharger un fichier CSV modèle pré-rempli avec 2 exemples."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modele_import_medicaments.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['code', 'nom', 'categorie', 'stock', 'stock_minimum', 'prix_achat', 'prix_vente', 'date_expiration', 'fournisseur_nom'])
    writer.writerow(['3011234567000', 'Paracetamol 500mg', 'Analgésique', 100, 10, 500, 750, '2027-12-31', "Pharmacie Nationale d'Approvisionnement (PNA)"])
    writer.writerow(['3011234567001', 'Amoxicilline 500mg', 'Antibiotique', 50, 5, 1200, 1800, '2027-06-30', ''])
    return response


@csrf_exempt
@api_role_required('superadmin', 'admin')
def api_import_csv(request):
    """Importer des médicaments depuis un fichier CSV (séparateur ; ou ,)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode invalide'}, status=405)

    uploaded_file = request.FILES.get('fichier_csv')
    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Aucun fichier reçu'}, status=400)

    try:
        raw_content = uploaded_file.read()
        try:
            content = raw_content.decode('utf-8-sig')
        except UnicodeDecodeError:
            content = raw_content.decode('latin-1')
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erreur de lecture: {e}'}, status=400)

    first_line = content.split('\n')[0]
    delimiter = ';' if first_line.count(';') >= first_line.count(',') else ','

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    required_cols = {'code', 'nom', 'categorie', 'prix_achat', 'prix_vente', 'date_expiration'}
    if not reader.fieldnames:
        return JsonResponse({'success': False, 'error': 'Fichier CSV vide ou mal formaté'}, status=400)

    actual_cols = {c.strip().lower() for c in reader.fieldnames}
    missing = required_cols - actual_cols
    if missing:
        return JsonResponse({
            'success': False,
            'error': f'Colonnes manquantes : {", ".join(missing)}. Téléchargez le modèle pour voir le bon format.'
        }, status=400)

    inserted = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        row = {k.strip().lower(): v.strip() for k, v in row.items() if k}

        code      = row.get('code', '').strip()
        nom       = row.get('nom', '').strip()
        categorie = row.get('categorie', '').strip()

        if not code or not nom or not categorie:
            errors.append(f"Ligne {i} ignorée : code, nom ou catégorie manquant.")
            continue

        try:
            stock       = int(float(row.get('stock', 0) or 0))
            stock_min   = int(float(row.get('stock_minimum', 5) or 5))
            prix_achat  = Decimal(str(row.get('prix_achat', 0) or 0).replace(',', '.'))
            prix_vente  = Decimal(str(row.get('prix_vente', 0) or 0).replace(',', '.'))
        except (ValueError, InvalidOperation) as e:
            errors.append(f"Ligne {i} ({nom}) ignorée : valeur numérique invalide → {e}")
            continue

        date_exp_str = row.get('date_expiration', '').strip()
        date_exp = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
            try:
                from datetime import datetime
                date_exp = datetime.strptime(date_exp_str, fmt).date()
                break
            except ValueError:
                continue
        if date_exp is None:
            errors.append(f"Ligne {i} ({nom}) ignorée : date d'expiration invalide '{date_exp_str}'.")
            continue

        fournisseur = None
        fourn_nom = row.get('fournisseur_nom', '').strip()
        if fourn_nom:
            fournisseur, _ = Fournisseur.objects.get_or_create(nom=fourn_nom)

        med, created = Medicament.objects.get_or_create(
            code=code,
            defaults={
                'nom': nom, 'categorie': categorie, 'stock': stock,
                'stock_minimum': stock_min, 'prix_achat': prix_achat,
                'prix_vente': prix_vente, 'date_expiration': date_exp,
                'fournisseur': fournisseur,
            }
        )

        if created:
            inserted += 1
            if stock > 0:
                MouvementStock.objects.create(
                    medicament=med, type_mouvement='ENTREE',
                    quantite=stock, motif='Import CSV initial'
                )
        else:
            med.nom = nom
            med.categorie = categorie
            med.stock_minimum = stock_min
            med.prix_achat = prix_achat
            med.prix_vente = prix_vente
            med.date_expiration = date_exp
            if fournisseur:
                med.fournisseur = fournisseur
            old_stock = med.stock
            med.stock = stock
            med.save()
            if old_stock != stock:
                MouvementStock.objects.create(
                    medicament=med, type_mouvement='AJUSTEMENT',
                    quantite=stock, motif='Mise à jour via import CSV'
                )
            updated += 1

    return JsonResponse({
        'success': True,
        'inserted': inserted,
        'updated': updated,
        'errors': errors,
        'total_processed': inserted + updated
    })


# ============================================================
# API GESTION DES UTILISATEURS (Super-Admin only)
# ============================================================

@api_role_required('superadmin')
def api_utilisateurs_liste(request):
    users = User.objects.all().order_by('id')
    data = []
    for u in users:
        role = get_user_role(u)
        display_name = f"{u.first_name} {u.last_name}".strip() if u.last_name not in ('admin', 'caissier') else u.first_name
        if not display_name:
            display_name = u.username
        data.append({
            'id': u.id,
            'nom': display_name,
            'username': u.username,
            'role': role,
            'is_active': u.is_active,
        })
    return JsonResponse({'users': data})

@csrf_exempt
@api_role_required('superadmin')
def api_utilisateur_save(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    data = json.loads(request.body)
    user_id = data.get('id')
    nom = data.get('nom', '').strip()
    username = data.get('username', '').strip()
    role = data.get('role', 'admin')
    password = data.get('password', '').strip()

    if not nom or not username:
        return JsonResponse({'success': False, 'error': 'Nom et identifiant requis.'})

    # Split nom into first/last for storage
    parts = nom.split(' ', 1)
    first_name = parts[0]
    last_name_display = parts[1] if len(parts) > 1 else ''

    if user_id:
        # Update existing user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Utilisateur introuvable.'})
        if user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Le super-administrateur ne peut pas être modifié ici.'})
        # Check username uniqueness
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            return JsonResponse({'success': False, 'error': f"L'identifiant '{username}' est déjà utilisé."})
        user.first_name = first_name
        # Store role in last_name field (simple approach)
        user.last_name = role  # 'admin' or 'caissier'
        user.username = username
        user.is_staff = (role == 'admin')
        if password:
            if len(password) < 4:
                return JsonResponse({'success': False, 'error': 'Le mot de passe doit contenir au moins 4 caractères.'})
            user.set_password(password)
        user.save()
        return JsonResponse({'success': True})
    else:
        # Create new user
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': f"L'identifiant '{username}' est déjà utilisé."})
        if not password or len(password) < 4:
            return JsonResponse({'success': False, 'error': 'Le mot de passe doit contenir au moins 4 caractères.'})
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=role,  # store role in last_name
            is_staff=(role == 'admin'),
            is_superuser=False,
        )
        return JsonResponse({'success': True})

@csrf_exempt
@api_role_required('superadmin')
def api_utilisateur_delete(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Utilisateur introuvable.'})
    if user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Impossible de supprimer le super-administrateur.'})
    if user == request.user:
        return JsonResponse({'success': False, 'error': 'Vous ne pouvez pas supprimer votre propre compte.'})
    user.delete()
    return JsonResponse({'success': True})


@api_role_required('superadmin', 'admin', 'caissier')
def api_current_user_info(request):
    """Returns current logged-in user info for the frontend navbar."""
    user = request.user
    role = get_user_role(user)
    display_name = user.get_full_name() or user.username
    # Clean up display name (remove role stored in last_name)
    if user.last_name in ('admin', 'caissier'):
        display_name = user.first_name or user.username
    return JsonResponse({
        'username': user.username,
        'display_name': display_name,
        'role': role,
        'initials': (display_name[:2]).upper() if display_name else 'U',
    })
