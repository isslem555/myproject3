from django.urls import path
from . import views

app_name = 'scraping_data'

urlpatterns = [
    # --- API Produits ---
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/fetch/', views.ProductFetchAPIView.as_view(), name='product-fetch'),

    # --- Swagger : rapport et scraping ---
    path('rapport-swagger/', views.afficher_rapport_swagger, name='rapport-swagger'),

    path('rapport-swagger/pdf/', views.rapport_swagger_pdf, name='rapport-swagger-pdf'),
    path('swagger/endpoints/', views.SwaggerScrapeAPIView.as_view(), name='swagger-endpoints'),
    path('lancer-scraping/', views.lancer_scraping, name='lancer-scraping'),

    # --- Gestion des projets Swagger ---
    path('list-projects/', views.list_projects, name='list-projects'),
    path('projects/add/', views.add_project, name='add-project'),
    path('projects/<int:pk>/edit/', views.edit_project, name='edit-project'),
    path('projects/<int:pk>/delete/', views.delete_project, name='delete-project'),
    path('projects/<int:pk>/parameters/', views.project_parameters, name='project-parameters'),

    # --- Test d'API ---
    path('tester/', views.tester_page, name='tester-page'),
    path('test_endpoint/', views.test_endpoint, name='test-endpoint'),
    path('download_history/', views.download_history, name='download-history'),
    path('clear-tests/', views.clear_tests, name='clear-tests'),
    path('tester-tous/', views.tester_tous, name='tester-tous'),

    # --- Génération des tests automatiques ---
    path('generate-test/', views.generate_test, name='generate_test'),
    path('run-tests/', views.run_tests, name='run-tests'),
    path('generate_report/', views.generate_test_report, name='generate-report'),

    # --- Page générée après test ---
    path('generate-test-page/', views.generate_test_page, name='generate_test_page'),
    path('test-endpoint/', views.test_endpoint, name='test-endpoint'),
    path('tester-tous/', views.tester_tous_endpoints, name='tester-tous'),
]

