import requests
import json
import os

# 📂 Chemin du fichier de produits local (utile pour tests CRUD)
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


# ✅ Lecture du fichier local des produits (si utilisé)
def get_products():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"erreur": "Fichier data.json introuvable."}


# ✅ Sauvegarde des produits dans data.json
def save_products(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ✅ Récupérer des produits depuis une fausse API (pour tests)
def fetch_products():
    url = "https://fakestoreapi.com/products"
    response = requests.get(url)
    if response.status_code == 200:
        produits = response.json()
        save_products(produits)
        return produits
    else:
        return {"erreur": "Échec de la récupération depuis l'API."}


# ✅ Scraper dynamique d’un fichier Swagger depuis une URL
def scrape_swagger(url="http://127.0.0.1:8000/swagger.json", user_email=None):
    """
    Scrape un Swagger JSON donné par URL.
    Si un email est donné, ajoute un token Bearer simulé dans les headers.
    Résultat : fichier swagger_report.json avec les endpoints extraits.
    """
    headers = {}

    if user_email:
        token = f"testtoken:{user_email}"
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Swagger JSON introuvable. Code {response.status_code}")

    swagger = response.json()
    result = []

    # 🔁 Analyse des chemins du Swagger
    for path, methods in swagger.get("paths", {}).items():
        for method, details in methods.items():
            if method == "parameters":  # Ignorer bloc global "parameters"
                continue

            endpoint_info = {
                "method": method.upper(),
                "endpoint": path,
                "summary": details.get("summary", ""),
                "parameters": []
            }

            for param in details.get("parameters", []):
                endpoint_info["parameters"].append({
                    "name": param.get("name"),
                    "in": param.get("in"),
                    "required": param.get("required", False),
                    "type": param.get("schema", {}).get("type", param.get("type", "object"))
                })

            result.append(endpoint_info)

    # 💾 Sauvegarde dans swagger_report.json (au niveau du projet)
    output_path = os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json')
    output_path = os.path.abspath(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)


# ✅ Extraction du fichier JSON généré pour l’affichage HTML
def extract_full_swagger_data():
    """
    Lecture du fichier swagger_report.json pour affichage dans vue Django
    """
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'swagger_report.json'))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"erreur": "Fichier swagger_report.json introuvable. Lancez d’abord /lancer-scraping."}
