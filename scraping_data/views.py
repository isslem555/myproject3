import os
import json

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.context_processors import csrf
from django.views.decorators.http import require_http_methods

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .scraper import (
    get_products,
    save_products,
    fetch_products,
    extract_full_swagger_data,
    scrape_swagger
)

from .serializers import ProductSerializer


# ✅ VUE HTML DYNAMIQUE — Affiche et scrappe dynamiquement le rapport Swagger
@csrf_exempt
@require_http_methods(["GET", "POST"])
def afficher_rapport_swagger(request):
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            url = body.get("swagger_url")

            if not url:
                return JsonResponse({"status": "erreur", "message": "URL Swagger manquante"})

            scrape_swagger(url=url)

            return JsonResponse({"status": "succès", "message": "Scraping terminé avec succès."})
        except Exception as e:
            return JsonResponse({"status": "erreur", "message": str(e)}, status=500)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    context = {'swagger_data': data}
    context.update(csrf(request))
    return render(request, 'rapport_swagger.html', context)


# Vue pour lancer le scraping Swagger avec URL + email (via curl ou API externe)
@csrf_exempt
@require_POST
def lancer_scraping(request):
    try:
        body = json.loads(request.body)
        url = body.get("url", "http://127.0.0.1:8000/swagger.json")
        email = body.get("email", None)

        scrape_swagger(url=url, user_email=email)

        return JsonResponse({"status": "succès", "message": "Scraping terminé avec succès."})
    except Exception as e:
        return JsonResponse({"status": "erreur", "message": str(e)}, status=500)


# Vue API dédiée — Scraping Swagger avec "swagger_url" et "email" (POST JSON)
@csrf_exempt
@require_POST
def lancer_scraping_url(request):
    try:
        body = json.loads(request.body)
        url = body.get("swagger_url")
        email = body.get("email", None)

        if not url:
            return JsonResponse({"status": "erreur", "message": "URL Swagger manquante"}, status=400)

        scrape_swagger(url=url, user_email=email)

        return JsonResponse({"status": "succès", "message": "Scraping terminé avec succès."})
    except Exception as e:
        msg = str(e)
        if "Code 401" in msg:
            msg += " — Veuillez vérifier votre token Bearer (email)."
        return JsonResponse({"status": "erreur", "message": msg}, status=500)


# Rapport PDF – Généré depuis swagger_report.json
def rapport_swagger_pdf(request):
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return HttpResponse("Fichier swagger_report.json introuvable", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=\"rapport_swagger.pdf\"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 2 * cm
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2 * cm, y, "Rapport des Endpoints Swagger")
    y -= 1.2 * cm

    for endpoint in data:
        if y < 3 * cm:
            p.showPage()
            y = height - 2 * cm
            p.setFont("Helvetica", 11)

        p.setFont("Helvetica-Bold", 10)
        p.drawString(2 * cm, y, f"{endpoint['method']} {endpoint['endpoint']}")
        y -= 0.5 * cm

        p.setFont("Helvetica", 9)
        p.drawString(2.2 * cm, y, f"{endpoint['summary']}")
        y -= 0.5 * cm

        for param in endpoint.get("parameters", []):
            if y < 2 * cm:
                p.showPage()
                y = height - 2 * cm
                p.setFont("Helvetica", 9)

            text = f" - {param['name']} ({param['in']}, {param['type']}, requis: {param['required']})"
            p.drawString(2.4 * cm, y, text)
            y -= 0.4 * cm

        y -= 0.5 * cm

    p.showPage()
    p.save()
    return response


# CRUD Produits

class ProductListView(APIView):
    @swagger_auto_schema(
        operation_summary="Lister les produits",
        operation_description="Retourne tous les produits avec filtres optionnels.",
        manual_parameters=[
            openapi.Parameter('min_price', openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('name', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request):
        data = get_products()
        q = request.query_params

        if 'min_price' in q:
            data = [p for p in data if p['price'] >= float(q['min_price'])]
        if 'max_price' in q:
            data = [p for p in data if p['price'] <= float(q['max_price'])]
        if 'category' in q:
            data = [p for p in data if p['category'].lower() == q['category'].lower()]
        if 'name' in q:
            data = [p for p in data if q['name'].lower() in p['title'].lower()]

        return Response(data)

    @swagger_auto_schema(operation_summary="Créer un produit", request_body=ProductSerializer)
    def post(self, request):
        data = get_products()
        serializer = ProductSerializer(data=request.data)

        if serializer.is_valid():
            new_product = serializer.data
            new_product['id'] = max([p['id'] for p in data], default=0) + 1
            data.append(new_product)
            save_products(data)
            return Response(new_product, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=400)


class ProductDetailView(APIView):
    @swagger_auto_schema(operation_summary="Modifier un produit", request_body=ProductSerializer)
    def put(self, request, pk):
        data = get_products()
        product = next((p for p in data if p['id'] == pk), None)

        if not product:
            return Response({"detail": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            updated_product = serializer.data
            updated_product['id'] = pk
            data[data.index(product)] = updated_product
            save_products(data)
            return Response(updated_product)

        return Response(serializer.errors, status=400)

    @swagger_auto_schema(operation_summary="Supprimer un produit")
    def delete(self, request, pk):
        data = get_products()
        product = next((p for p in data if p['id'] == pk), None)

        if not product:
            return Response({"detail": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        data.remove(product)
        save_products(data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductFetchAPIView(APIView):
    @swagger_auto_schema(operation_summary="Récupérer les produits depuis API externe")
    def post(self, request):
        data = fetch_products()
        if "erreur" in data:
            return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"status": "succès", "produits": data}, status=status.HTTP_200_OK)


class ReportPDFView(APIView):
    @swagger_auto_schema(operation_summary="Télécharger un rapport PDF de test")
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="rapport.pdf"'
        p = canvas.Canvas(response)
        p.drawString(100, 800, "Rapport automatique généré")
        p.showPage()
        p.save()
        return response


class SwaggerScrapeAPIView(APIView):
    @swagger_auto_schema(operation_summary="Lister les endpoints Swagger")
    def get(self, request):
        data = extract_full_swagger_data()
        return Response(data)
