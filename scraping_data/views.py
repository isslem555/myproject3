import os
import json
from collections import Counter
import requests
import io
from urllib.parse import urlparse
import subprocess

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django import forms
from django.conf import settings
from django.contrib import messages

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .models import SwaggerProject, SwaggerEndpoint  # adapte selon ton modèle


# --------- Formulaire Django pour SwaggerProject ---------
class SwaggerProjectForm(forms.ModelForm):
    class Meta:
        model = SwaggerProject
        fields = ['name', 'swagger_url']


# --------- Vues CRUD Django classiques ---------
def list_projects(request):
    projets = SwaggerProject.objects.all().order_by('-created_at')

    for p in projets:
        parsed_url = urlparse(p.swagger_url)
        p.swagger_root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    return render(request, 'list_projects.html', {'projets': projets})


def add_project(request):
    if request.method == "POST":
        form = SwaggerProjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('scraping_data:list-projects')
    else:
        form = SwaggerProjectForm()
    return render(request, 'project_form.html', {'form': form, 'title': 'Ajouter un projet'})


def edit_project(request, pk):
    projet = get_object_or_404(SwaggerProject, pk=pk)
    if request.method == "POST":
        form = SwaggerProjectForm(request.POST, instance=projet)
        if form.is_valid():
            form.save()
            return redirect('scraping_data:list-projects')
    else:
        form = SwaggerProjectForm(instance=projet)
    return render(request, 'project_form.html', {'form': form, 'title': 'Modifier le projet'})


@require_POST
def delete_project(request, pk):
    projet = get_object_or_404(SwaggerProject, pk=pk)
    projet.delete()
    return redirect('scraping_data:list-projects')


# --------- Vue pour afficher uniquement les headers ---------
def project_parameters(request, pk):
    projet = get_object_or_404(SwaggerProject, pk=pk)
    swagger_json = projet.swagger_json or []

    headers = []
    seen_names = set()

    for ep in swagger_json:
        for param in ep.get("parameters", []):
            if param.get("in") == "header":
                name = param.get("name")
                if name and name not in seen_names:
                    headers.append({
                        "name": name,
                        "type": param.get("type", ""),
                        "required": param.get("required", False),
                        "example": param.get("value", ""),
                    })
                    seen_names.add(name)

    context = {
        'projet': projet,
        'headers': headers,
    }
    return render(request, 'project_parameters.html', context)


# --------- Sérializers exemple produits ---------
class ProductSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField()
    price = serializers.FloatField()
    category = serializers.CharField()


# --------- Gestion produits fictifs ---------
PRODUCTS = [
    {"id": 1, "title": "Produit A", "price": 10.0, "category": "cat1"},
    {"id": 2, "title": "Produit B", "price": 15.5, "category": "cat2"},
]

def get_products():
    return PRODUCTS

def save_products(data):
    global PRODUCTS
    PRODUCTS = data


# --------- API views produits (CRUD + fetch) ---------
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


class ProductFetchAPIView(APIView):
    def post(self, request):
        data = [{"id": 3, "title": "Produit C", "price": 20, "category": "cat3"}]
        return Response({"status": "succès", "produits": data})


# --------- Scraping Swagger JSON ---------
def scrape_swagger(url):
    response = requests.get(url)
    response.raise_for_status()
    swagger_json = response.json()

    endpoints = []
    paths = swagger_json.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            summary = details.get("summary", "") or details.get("description", "")
            if "IGNORE THIS ENDPOINT FOR NOW" in summary:
                continue

            endpoint = {
                "method": method.upper(),
                "endpoint": path,
                "summary": summary,
                "parameters": []
            }

            for param in details.get("parameters", []):
                param_type = ""
                if "schema" in param and param["schema"]:
                    param_type = param["schema"].get("type", "")
                else:
                    param_type = param.get("type", "")

                param_value = param.get("example")
                if param_value is None:
                    param_value = param.get("default", "valeur")

                endpoint["parameters"].append({
                    "name": param.get("name", ""),
                    "in": param.get("in", ""),
                    "type": param_type,
                    "required": param.get("required", False),
                    "value": param_value
                })

            if "requestBody" in details:
                content = details["requestBody"].get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    props = schema.get("properties", {})
                    required_props = schema.get("required", [])
                    for name, prop in props.items():
                        param_type = prop.get("type", "")
                        example_value = prop.get("example")
                        if example_value is None:
                            example_value = prop.get("default", "valeur")

                        endpoint["parameters"].append({
                            "name": name,
                            "in": "body",
                            "type": param_type,
                            "required": name in required_props,
                            "value": example_value
                        })

            endpoints.append(endpoint)

    return endpoints


def enrich_and_save(swagger_data, url):
    base_url = url.rstrip("/")

    for ep in swagger_data:
        method = ep.get("method", "GET").upper()
        endpoint_path = ep.get("endpoint", "")

        query_params = []
        for param in ep.get("parameters", []):
            if param.get("in") == "query":
                name = param.get("name")
                value = param.get("value", "valeur")
                query_params.append(f"{name}={value}")

        query_string = "&".join(query_params)
        full_url = f"{base_url}{endpoint_path}"
        if query_string:
            full_url += f"?{query_string}"

        ep["url_complete"] = full_url

    # Sauvegarde dans fichier JSON local
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json')
    )
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(swagger_data, f, ensure_ascii=False, indent=2)

    return swagger_data


@csrf_exempt
@require_http_methods(["GET", "POST"])
def afficher_rapport_swagger(request):
    project_id = request.GET.get("id")
    swagger_data = []
    base_url = None

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            url = body.get("swagger_url")
            if not url:
                return JsonResponse({"status": "erreur", "message": "URL Swagger manquante"}, status=400)

            swagger_data = scrape_swagger(url)
            swagger_data = enrich_and_save(swagger_data, url)

            SwaggerProject.objects.create(
                name=None,
                swagger_url=url,
                swagger_json=swagger_data
            )

            request.session['swagger_base_url'] = url.rstrip("/")
            return JsonResponse({"status": "succès", "message": "Scraping terminé.", "data": swagger_data})

        except Exception as e:
            return JsonResponse({"status": "erreur", "message": str(e)}, status=500)

    if project_id:
        projet = get_object_or_404(SwaggerProject, pk=project_id)
        swagger_data = projet.swagger_json or []
        base_url = projet.swagger_url
    else:
        file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json')
        )
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                swagger_data = json.load(f)
            base_url = request.session.get('swagger_base_url', None)
        except FileNotFoundError:
            swagger_data = []

    method_counter = Counter(
        ep.get("method", "UNKNOWN").upper() for ep in swagger_data
    )
    total_params = sum(
        len(ep.get("parameters", [])) for ep in swagger_data
    )
    stats = {
        "methods": list(method_counter.items()),
        "avg_params": round(total_params / len(swagger_data), 2) if swagger_data else 0,
    }

    context = {
        "swagger_data": swagger_data,
        "stats": stats,
        "base_url": base_url,
    }
    return render(request, "rapport_swagger.html", context)


@require_POST
def lancer_scraping(request):
    url = request.POST.get('swagger_url')
    if not url:
        messages.error(request, "L'URL Swagger est manquante.")
        return redirect('scraping_data:generate_test_page')

    try:
        swagger_data = scrape_swagger(url)
        swagger_data = enrich_and_save(swagger_data, url)

        SwaggerProject.objects.create(
            name=None,
            swagger_url=url,
            swagger_json=swagger_data
        )

        messages.success(request, "Scraping lancé avec succès.")
        return redirect('scraping_data:rapport-swagger')

    except Exception as e:
        messages.error(request, f"Erreur lors du scraping : {e}")
        return redirect('scraping_data:generate_test_page')


def rapport_swagger_pdf(request):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.drawString(100, 800, "Rapport Swagger PDF")
    p.drawString(100, 780, "Ceci est un exemple de génération de PDF.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='rapport_swagger.pdf')


# ======================= VUES TEST API ========================
test_history = []

def tester_page(request):
    return render(request, "tester.html")


@csrf_exempt
@require_POST
def test_endpoint(request):
    data = json.loads(request.body.decode('utf-8'))
    method = data.get('method', 'GET')
    url = data.get('url', '')
    params = data.get('params', {})
    path_vars = data.get('path_vars', {})
    body = data.get('body', {})
    headers = data.get('headers', {})

    if 'api.nasa.gov' in url and 'api_key' not in params:
        return JsonResponse({
            'status': 'error',
            'error': 'Clé API NASA (api_key) requise pour cet endpoint'
        }, status=400)

    formatted_url = url
    for key, value in path_vars.items():
        formatted_url = formatted_url.replace(f'{{{key}}}', value)

    try:
        resp = requests.request(
            method,
            formatted_url,
            params=params,
            json=body if body else None,
            headers=headers,
            timeout=5
        )

        if 200 <= resp.status_code <= 299:
            test_status = "succeeded" if resp.status_code == 201 else "passed"
        else:
            test_status = "failed"

        entry = {
            'timestamp': timezone.now().isoformat(),
            'method': method,
            'url': formatted_url,
            'params': params,
            'path_vars': path_vars,
            'body': body,
            'headers': headers,
            'status_code': resp.status_code,
            'response': resp.text,
            'test_status': test_status,
        }
        test_history.append(entry)

        return JsonResponse({
            'status': 'success',
            'status_code': resp.status_code,
            'response': resp.text,
            'request_body': body
        })

    except requests.RequestException as e:
        entry = {
            'timestamp': timezone.now().isoformat(),
            'method': method,
            'url': formatted_url,
            'params': params,
            'path_vars': path_vars,
            'body': body,
            'headers': headers,
            'status_code': 500,
            'response': str(e),
            'test_status': 'failed'
        }
        test_history.append(entry)
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


def download_history(request):
    buffer = io.StringIO()
    json.dump(test_history, buffer, indent=2)
    buffer.seek(0)
    mem = io.BytesIO()
    mem.write(buffer.getvalue().encode('utf-8'))
    mem.seek(0)
    response = HttpResponse(mem, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename=test_history.json'
    return response


# ======================= VUE POUR RAPPORT PYTEST ========================
def generate_test_report(request):
    """
    Lance pytest et génère un rapport HTML dans un fichier temporaire.
    Renvoie ensuite le fichier en téléchargement.
    """
    report_path = os.path.join(settings.BASE_DIR, "pytest_report.html")
    subprocess.run([
        "pytest",
        "--disable-warnings",
        "--maxfail=1",
        "--html=" + report_path,
        "--self-contained-html"
    ], cwd=settings.BASE_DIR)

    with open(report_path, "rb") as f:
        response = HttpResponse(f.read(), content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename=rapport_tests.html'
        return response


# ====== Fonction pour lancer les tests sur tous les endpoints =======
def run_tests(request):
    endpoints = SwaggerEndpoint.objects.all()
    results = []

    for ep in endpoints:
        try:
            response = requests.get(ep.url_complete, timeout=5)
            results.append({
                "endpoint": ep.url_complete,
                "success": response.status_code == 200,
                "message": f"{response.status_code} {response.reason}"
            })
        except Exception as e:
            results.append({
                "endpoint": ep.url_complete,
                "success": False,
                "message": str(e)
            })

    return JsonResponse({"status": "ok", "results": results})


from django.shortcuts import redirect
from django.contrib import messages

def generate_test(request):
    # Traitement pour générer un test ici...
    messages.success(request, "Le test a été généré avec succès.")
    return redirect('scraping_data:generate_test_page')  # <-- Utilisation du namespace

def generate_test_page(request):
    return render(request, 'generate_test.html')


def tester_tous(request):
    messages.success(request, "Tous les endpoints ont été testés avec succès.")
    return redirect('scraping_data:rapport-swagger')


def clear_tests(request):
    global test_history
    test_history = []
    messages.info(request, "Les résultats de test ont été effacés.")
    return redirect('scraping_data:rapport-swagger')

from rest_framework.views import APIView
from rest_framework.response import Response

class SwaggerScrapeAPIView(APIView):
    def get(self, request):
        projects = SwaggerProject.objects.all()
        all_endpoints = []
        for projet in projects:
            swagger_json = projet.swagger_json or []
            all_endpoints.extend(swagger_json)
        return Response(all_endpoints)

import json
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.utils import timezone
from scraping_data.models import SwaggerEndpoint  # à adapter selon ton modèle

test_history = []

@csrf_exempt
def tester_tous_endpoints(request):
    endpoints = SwaggerEndpoint.objects.all()  # récupère les endpoints depuis la DB

    results = []

    for ep in endpoints:
        payload = {
            'method': ep.method,
            'url': ep.url_complete,
            'params': ep.params or {},
            'path_vars': ep.path_vars or {},
            'body': ep.body or {},
            'headers': ep.headers or {},
        }

        try:
            # Appelle la même logique que `test_endpoint`
            response = requests.post(
                request.build_absolute_uri('/api/test-endpoint/'),
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            res_data = response.json()
            results.append({
                'endpoint': ep.url_complete,
                'status': res_data.get('status', 'error'),
                'details': res_data.get('response', '')[:200]
            })
        except Exception as e:
            results.append({
                'endpoint': ep.url_complete,
                'status': 'error',
                'details': str(e)
            })

    return render(request, 'swagger/test_results.html', {'results': results})


from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

# ======================= ✅ NOUVELLE VUE CLEAN TESTS ========================
@csrf_exempt
@require_POST
def clean_tests(request):
    """
    Réinitialise l'historique des tests.
    """
    global test_history
    test_history.clear()
    return JsonResponse({"status": "succès", "message": "Historique des tests nettoyé."})