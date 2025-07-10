from scraping_data.swagger_scraper import scrape_swagger

if __name__ == "__main__":
    scrape_swagger("http://127.0.0.1:8000/swagger/?format=openapi")
