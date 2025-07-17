from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductFetchAPIView,
    SwaggerScrapeAPIView,
    afficher_rapport_swagger,
    rapport_swagger_pdf,
    lancer_scraping,
    list_projects,
    add_project,
    edit_project,
    delete_project,
    project_parameters,  # ✅ import de la vue pour les paramètres du projet
    tester_page,         # ✅ import de la vue tester_page
    test_endpoint,       # ✅ import de la vue test_endpoint
    download_history,    # ✅ import de la vue download_history
    generate_test_report # ✅ import de la vue pour générer le rapport pytest
)

app_name = 'scraping_data'

urlpatterns = [
    # --- API Produits ---
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/fetch/', ProductFetchAPIView.as_view(), name='product-fetch'),

    # --- Swagger : rapport et scraping ---
    path('rapport-swagger/', afficher_rapport_swagger, name='rapport-swagger-html'),
    path('rapport-swagger/pdf/', rapport_swagger_pdf, name='rapport-swagger-pdf'),
    path('swagger/endpoints/', SwaggerScrapeAPIView.as_view(), name='swagger-endpoints'),
    path('lancer-scraping/', lancer_scraping, name='lancer-scraping'),

    # --- Gestion des projets Swagger ---
    path('list-projects/', list_projects, name='list-projects'),
    path('projects/add/', add_project, name='add-project'),
    path('projects/<int:pk>/edit/', edit_project, name='edit-project'),
    path('projects/<int:pk>/delete/', delete_project, name='delete-project'),

    # --- Nouvelle URL pour afficher les paramètres du projet ---
    path('projects/<int:pk>/parameters/', project_parameters, name='project-parameters'),

    # --- ✅ Nouvelles routes pour tester les API ---
    path('tester/', tester_page, name='tester-page'),
    path('test_endpoint/', test_endpoint, name='test-endpoint'),
    path('download_history/', download_history, name='download-history'),

    # --- ✅ Nouvelle route pour générer le rapport pytest ---
    path('generate_report/', generate_test_report, name='generate-report'),
]
