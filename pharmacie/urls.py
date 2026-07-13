from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Pages HTML
    path('', views.dashboard, name='dashboard'),
    path('medicaments/', views.liste_medicaments, name='liste_medicaments'),
    path('stocks/', views.gestion_stocks, name='gestion_stocks'),
    path('alertes/', views.alertes_page, name='alertes_page'),
    path('ventes/', views.gestion_ventes, name='gestion_ventes'),
    path('fournisseurs/', views.gestion_fournisseurs, name='gestion_fournisseurs'),
    path('rapports/', views.rapports_page, name='rapports_page'),
    path('utilisateurs/', views.utilisateurs_page, name='utilisateurs_page'),
    
    # API endpoints
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    
    path('api/medicaments/', views.api_medicaments_liste, name='api_medicaments_liste'),
    path('api/medicaments/save/', views.api_medicament_save, name='api_medicament_save'),
    path('api/medicaments/delete/<int:med_id>/', views.api_medicament_delete, name='api_medicament_delete'),
    
    path('api/stocks/mouvement/', views.api_stock_mouvement, name='api_stock_mouvement'),
    path('api/stocks/historique/', views.api_stock_historique, name='api_stock_historique'),
    
    path('api/fournisseurs/', views.api_fournisseurs_liste, name='api_fournisseurs_liste'),
    path('api/fournisseurs/save/', views.api_fournisseur_save, name='api_fournisseur_save'),
    path('api/fournisseurs/delete/<int:f_id>/', views.api_fournisseur_delete, name='api_fournisseur_delete'),
    
    path('api/ventes/creer/', views.api_vente_creer, name='api_vente_creer'),
    path('api/ventes/historique/', views.api_ventes_historique, name='api_ventes_historique'),
    path('api/ventes/<int:vente_id>/annuler/', views.api_vente_annuler, name='api_vente_annuler'),  # ✅ NOUVEAU
    path('facture/<int:vente_id>/print/', views.api_facture_pdf, name='api_facture_print'),
    
    path('api/rapports/', views.api_rapports_data, name='api_rapports_data'),
    path('api/peupler/', views.api_peupler_db, name='api_peupler_db'),

    # Import CSV en masse
    path('api/import/template/', views.api_import_template, name='api_import_template'),
    path('api/import/csv/', views.api_import_csv, name='api_import_csv'),

    # User management API
    path('api/utilisateurs/', views.api_utilisateurs_liste, name='api_utilisateurs_liste'),
    path('api/utilisateurs/save/', views.api_utilisateur_save, name='api_utilisateur_save'),
    path('api/utilisateurs/delete/<int:user_id>/', views.api_utilisateur_delete, name='api_utilisateur_delete'),
    path('api/me/', views.api_current_user_info, name='api_current_user_info'),
]
