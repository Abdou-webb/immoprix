# Pipelines

## Pipeline complet
Scraping -> Prétraitement -> Modélisation XGBoost -> Modèles sauvegardés

## Étapes détaillées
1. **Scraping** : collecter les données via Selenium (Mubawab) et Scrapy (Avito)
2. **Prétraitement** : nettoyer, normaliser, générer les features
3. **Entraînement** : entraîner le modèle XGBoost sur features tabulaires
4. **Sauvegarde** : sauvegarder le modèle entraîné pour une utilisation ultérieure
