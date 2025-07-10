from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductFetchAPIView,
    ReportPDFView,
    SwaggerScrapeAPIView,
    afficher_rapport_swagger,     # ✅ Vue HTML dynamique avec formulaire
    rapport_swagger_pdf,          # ✅ Rapport PDF
    lancer_scraping,              # ✅ Scraping API local
    lancer_scraping_url           # ✅ Scraping Swagger depuis URL (AJAX/POST)
)

urlpatterns = [
    # 🛒 Produits (CRUD + fetch externe)
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/fetch/', ProductFetchAPIView.as_view(), name='product-fetch'),

    # 📄 Rapport PDF
    path('reports/pdf/', ReportPDFView.as_view(), name='report-pdf'),

    # 📊 Endpoints Swagger depuis projet local
    path('swagger/endpoints/', SwaggerScrapeAPIView.as_view(), name='swagger-endpoints'),

    # 🌐 Rapport Swagger - Affichage HTML
    path('rapport-swagger/', afficher_rapport_swagger, name='rapport-swagger-html'),

    # 📄 Rapport Swagger - PDF
    path('rapport-swagger/pdf/', rapport_swagger_pdf, name='rapport-swagger-pdf'),

    # 🔁 Scraping local
    path('lancer-scraping/', lancer_scraping, name='lancer-scraping'),

    # 🔁 Scraping Swagger externe via URL JSON (utilisé par JS dans formulaire)
    path('lancer-scraping-url/', lancer_scraping_url, name='lancer-scraping-url'),
]
