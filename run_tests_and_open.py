import os
import webbrowser
from pathlib import Path

# Génère le rapport
os.system("pytest --html=rapport.html --self-contained-html")

# Obtenir le chemin absolu vers le rapport HTML
rapport_path = Path("rapport.html").resolve().as_uri()

# Ouvre dans le navigateur par défaut (Chrome ou autre)
webbrowser.open(rapport_path)
chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
webbrowser.get(chrome_path).open(rapport_path)