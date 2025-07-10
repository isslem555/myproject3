from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductFetchAPIView,
    ReportPDFView,
    SwaggerScrapeAPIView,
    afficher_rapport_swagger,
    rapport_swagger_pdf,
    lancer_scraping,
    lancer_scraping_url,
    statistiques_swagger
)

urlpatterns = [
    # Produits (CRUD + fetch externe)
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/fetch/', ProductFetchAPIView.as_view(), name='product-fetch'),

    # Rapport PDF
    path('reports/pdf/', ReportPDFView.as_view(), name='report-pdf'),

    # Endpoints Swagger depuis projet local (requête POST avec URL swagger à scraper)
    path('swagger/endpoints/', SwaggerScrapeAPIView.as_view(), name='swagger-endpoints'),

    # Rapport Swagger - Affichage HTML dynamique avec formulaire
    path('rapport-swagger/', afficher_rapport_swagger, name='rapport-swagger-html'),

    # Rapport Swagger - PDF
    path('rapport-swagger/pdf/', rapport_swagger_pdf, name='rapport-swagger-pdf'),

    # Scraping local (POST avec URL)
    path('lancer-scraping/', lancer_scraping, name='lancer-scraping'),

    # Scraping Swagger externe via URL JSON (utilisé par JS dans formulaire)
    path('lancer-scraping-url/', lancer_scraping_url, name='lancer-scraping-url'),

    # Page dédiée aux statistiques Swagger
    path('rapport-swagger/statistiques/', statistiques_swagger, name='swagger-statistiques'),
]
