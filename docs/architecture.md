# Architecture du projet Real Estate Price Prediction

## Aperçu
Le projet suit une architecture modulaire pour la collecte et la modélisation des données :

- **Adaptateurs d'entrée** : Scraping avec Selenium (Mubawab) et Scrapy (Avito)
- **Domaine métier** : Nettoyage, feature engineering, modèles ML
- **Adaptateurs de sortie** : Modèles entraînés et données nettoyées

## Schéma
[Scraping] --> [Preprocessing] --> [XGBoost Training] --> [Saved Models]

## Modules
- `scrap/` : collecte des données via Selenium et Scrapy
- `preprocessing/` : nettoyage et préparation des données
- `models/` : entraînement du modèle XGBoost
