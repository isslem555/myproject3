import os
import json
from collections import Counter
import requests

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm


# --- Serializer produit ---
class ProductSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField()
    price = serializers.FloatField()
    category = serializers.CharField()


# --- Base produits en mémoire ---
PRODUCTS = [
    {"id": 1, "title": "Produit A", "price": 10.0, "category": "cat1"},
    {"id": 2, "title": "Produit B", "price": 15.5, "category": "cat2"},
]

def get_products():
    return PRODUCTS

def save_products(data):
    global PRODUCTS
    PRODUCTS = data


# --- Liste produits ---
class ProductListView(APIView):
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

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            data = get_products()
            new_product = serializer.validated_data
            new_product['id'] = max([p['id'] for p in data], default=0) + 1
            data.append(new_product)
            save_products(data)
            return Response(new_product, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)


# --- Détail produit ---
class ProductDetailView(APIView):
    def put(self, request, pk):
        data = get_products()
        product = next((p for p in data if p['id'] == pk), None)
        if not product:
            return Response({"detail": "Produit non trouvé"}, status=404)

        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            updated_product = serializer.validated_data
            updated_product['id'] = pk
            data[data.index(product)] = updated_product
            save_products(data)
            return Response(updated_product)

        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        data = get_products()
        product = next((p for p in data if p['id'] == pk), None)
        if not product:
            return Response({"detail": "Produit non trouvé"}, status=404)

        data.remove(product)
        save_products(data)
        return Response(status=204)


# --- Fetch externe produit (exemple) ---
class ProductFetchAPIView(APIView):
    def post(self, request):
        data = [{"id": 3, "title": "Produit C", "price": 20, "category": "cat3"}]
        return Response({"status": "succès", "produits": data})


# --- Rapport PDF simple ---
class ReportPDFView(APIView):
    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="rapport.pdf"'
        p = canvas.Canvas(response, pagesize=A4)
        p.drawString(100, 800, "Rapport PDF exemple")
        p.showPage()
        p.save()
        return response


# --- Scraping Swagger minimal ---
class SwaggerScrapeAPIView(APIView):
    def get(self, request):
        data = [
            {"method": "GET", "endpoint": "/api/products/", "summary": "Liste des produits", "parameters": []},
            {"method": "POST", "endpoint": "/api/products/", "summary": "Créer un produit", "parameters": []},
        ]
        return Response(data)


# --- Fonction scrape swagger ---
def scrape_swagger(url):
    response = requests.get(url)
    response.raise_for_status()
    swagger_json = response.json()

    endpoints = []
    paths = swagger_json.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            endpoint = {
                "method": method.upper(),
                "endpoint": path,
                "summary": details.get("summary", ""),
                "parameters": []
            }
            for param in details.get("parameters", []):
                endpoint["parameters"].append({
                    "name": param.get("name", ""),
                    "in": param.get("in", ""),
                    "type": param.get("schema", {}).get("type", "") if param.get("schema") else param.get("type", ""),
                    "required": param.get("required", False)
                })
            endpoints.append(endpoint)

    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(endpoints, f, ensure_ascii=False, indent=2)

    return endpoints


# --- Vue HTML rapport swagger + scraping dynamique ---
@csrf_exempt
@require_http_methods(["GET", "POST"])
def afficher_rapport_swagger(request):
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            url = body.get("swagger_url")
            if not url:
                return JsonResponse({"status": "erreur", "message": "URL Swagger manquante"}, status=400)

            swagger_data = scrape_swagger(url=url)
            return JsonResponse({"status": "succès", "message": "Scraping terminé.", "data": swagger_data})

        except Exception as e:
            return JsonResponse({"status": "erreur", "message": str(e)}, status=500)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            swagger_data = json.load(f)
    except FileNotFoundError:
        swagger_data = []

    method_counter = Counter(ep.get("method", "UNKNOWN").upper() for ep in swagger_data)
    total_params = sum(len(ep.get("parameters", [])) for ep in swagger_data)
    secured = sum(1 for ep in swagger_data if any("auth" in p.get("name", "").lower() for p in ep.get("parameters", [])))
    unsecured = len(swagger_data) - secured

    stats = {
        "methods": list(method_counter.items()),
        "methods_keys": list(method_counter.keys()),
        "methods_values": list(method_counter.values()),
        "avg_params": round(total_params / len(swagger_data), 2) if swagger_data else 0,
        "secured": secured,
        "unsecured": unsecured
    }

    from django.template.context_processors import csrf
    context = {
        "swagger_data": swagger_data,
        "stats": stats,
    }
    context.update(csrf(request))

    return render(request, 'rapport_swagger.html', context)


# --- Rapport swagger PDF ---
def rapport_swagger_pdf(request):
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return HttpResponse("Fichier swagger_report.json introuvable", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_swagger.pdf"'

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


# --- Vues pour lancer scraping via POST (facultatif) ---
@csrf_exempt
@require_POST
def lancer_scraping(request):
    try:
        body = json.loads(request.body)
        url = body.get("url")
        if not url:
            return JsonResponse({"status": "erreur", "message": "URL manquante"}, status=400)

        scrape_swagger(url=url)

        return JsonResponse({"status": "succès", "message": "Scraping lancé avec succès."})
    except Exception as e:
        return JsonResponse({"status": "erreur", "message": str(e)}, status=500)


@csrf_exempt
@require_POST
def lancer_scraping_url(request):
    try:
        body = json.loads(request.body)
        url = body.get("swagger_url")
        if not url:
            return JsonResponse({"status": "erreur", "message": "URL Swagger manquante"}, status=400)

        scrape_swagger(url=url)

        return JsonResponse({"status": "succès", "message": "Scraping Swagger via URL réussi."})
    except Exception as e:
        return JsonResponse({"status": "erreur", "message": str(e)}, status=500)


# --- Nouvelle vue : Statistiques Swagger ---
def statistiques_swagger(request):
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            swagger_data = json.load(f)
    except FileNotFoundError:
        swagger_data = []

    method_counter = Counter(ep.get("method", "UNKNOWN").upper() for ep in swagger_data)
    total_params = sum(len(ep.get("parameters", [])) for ep in swagger_data)
    secured = sum(1 for ep in swagger_data if any("auth" in p.get("name", "").lower() for p in ep.get("parameters", [])))
    unsecured = len(swagger_data) - secured

    stats = {
        "methods": list(method_counter.items()),
        "methods_keys": list(method_counter.keys()),
        "methods_values": list(method_counter.values()),
        "avg_params": round(total_params / len(swagger_data), 2) if swagger_data else 0,
        "secured": secured,
        "unsecured": unsecured
    }

    context = {
        "stats": stats
    }
    return render(request, 'swagger_statistiques.html', context)
