from django.db import models

class Product(models.Model):
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title


class SwaggerProject(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    swagger_url = models.URLField()
    swagger_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Swagger Project {self.id}"
