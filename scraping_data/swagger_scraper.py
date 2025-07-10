import requests
import json
SWAGGER_URL = "http://127.0.0.1:8000/swagger/?format=openapi"

def scrape_swagger(url=SWAGGER_URL):
    try:
        response = requests.get(url)
        response.raise_for_status()
        swagger_data = response.json()

        results = []

        paths = swagger_data.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                # Ignorer la clé "parameters" qui n'est pas une méthode HTTP
                if method == "parameters":
                    continue

                # Vérifier que details est bien un dictionnaire
                if not isinstance(details, dict):
                    continue

                # Construire le dictionnaire avec l'ordre des clés souhaité
                endpoint_info = {
                    "method": method.upper(),
                    "endpoint": path,
                    "summary": details.get("summary", ""),
                    "parameters": []
                }

                parameters = details.get("parameters", [])
                for param in parameters:
                    param_type = param.get("type")
                    if not param_type and "schema" in param:
                        param_type = param["schema"].get("type", "unknown")

                    endpoint_info["parameters"].append({
                        "name": param.get("name"),
                        "in": param.get("in"),
                        "required": param.get("required", False),
                        "type": param_type if param_type else "unknown"
                    })

                results.append(endpoint_info)

        with open("swagger_report.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        print("✅ Rapport Swagger généré dans swagger_report.json")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de requête : {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de décodage JSON : {e}")

if __name__ == "__main__":
    scrape_swagger()
