# ⚡ QUICK START GUIDE - PRÉDICTION EN 5 MINUTES

## 🎯 Objectif
Obtenir une prédiction de prix immobilier avec vos propres données.

---

## ✅ Prérequis

- Python 3.10+
- PostgreSQL avec base de données `real` (optionnel - utiliser données existantes)
- Données nettoyées dans PostgreSQL table `combine`

---

## 🚀 Lancement Rapide

### **Étape 1: Préparation (2 minutes)**

```bash
# Cloner et accéder au projet
cd real-estate-price-prediction

# Activer l'environnement virtuel
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Installer dépendances (si nécessaire)
pip install -r requirements.txt
```

---

### **Étape 2: Entraîner le modèle (10-15 minutes)**

⚠️ **À faire une seule fois!**

```bash
cd src/models/Xgboost
python train.py
```

**Le script va:**
- ✅ Charger 30,000+ propriétés depuis PostgreSQL
- ✅ Optimiser le modèle (50 iterations)
- ✅ Sauvegarder `real_estate_model_*.joblib`

**Sortie attendue:**
```
✅ Model loaded for: For Sale
📊 Number of features: 24
✅ Feature engineering completed!
💰 Base Predicted Price: 2,500,000 MAD
```

---

### **Étape 3: FAIRE UNE PRÉDICTION** ⭐

Choisissez UNE des 3 options:

#### **OPTION A: Interface Interactive (Facile)**

```bash
cd src/models/Xgboost
python prediction_app.py
```

Puis sélectionnez option 1 ou 2 dans le menu.

```
🏠 MOROCCAN REAL ESTATE PRICE PREDICTION SYSTEM 🏠
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPTIONS:
  1. Enter new property manually
  2. Use example property  
  3. View feature importance
  4. Exit

Select option (1-4): 1
```

Entrez les données demandées → Obtenez la prédiction immédiatement!

---

#### **OPTION B: Jupyter Notebook (Recommandé)**

```bash
jupyter notebook predict_price.ipynb
```

- Interface visuelle
- Pas besoin de ligne de commande
- Visualisations incluses
- Idéal pour présentation

**Étapes dans le notebook:**
1. Exécutez les cellules une par une
2. Entrez vos données quand demandé
3. Visualisez les résultats

---

#### **OPTION C: Python Script (Simple)**

```bash
cd src/models/Xgboost
python predict.py
```

Cela utilisera l'exemple fourni et affichera la prédiction.

---

## 📊 Exemple Complet

```python
# Données d'entrée
location = "Guéliz, Marrakech"
surface = 150  # m²
rooms = 6
bedrooms = 3
bathrooms = 2
property_category = "Apartment"
listing_type = "For Sale"
amenities = {
    'terrace': True,
    'garage': True,
    'pool': False,
    'security': True
}

# Résultat
💰 PREDICTED PRICE: 2,500,000 MAD
📐 Price per m²: 16,667 MAD/m²
📊 Range: 2,250,000 - 2,750,000 MAD (±10%)
```

---

## 🆘 Problèmes Courants

### Erreur: "No trained model found"

```bash
# Solution: Entraînez d'abord le modèle
cd src/models/Xgboost
python train.py
```

### Erreur: "Connection refused" PostgreSQL

```bash
# Vérifiez que PostgreSQL est lancé
# Windows: pg_ctl -D "C:\Program Files\PostgreSQL\data" start
# Linux: sudo systemctl start postgresql

# Ou utilisez les données déjà en cache
```

### Erreur: "Module not found"

```bash
# Réinstallez les dépendances
pip install -r requirements.txt
```

---

## 📁 Fichiers Clés

```
src/models/Xgboost/
├── train.py              # Entraîner (1x au début)
├── predict.py            # Module de prédiction
├── prediction_app.py     # Interface interactive (PLUS FACILE!)
└── real_estate_model_*.joblib  # Modèles (auto-générés)

/ 
└── predict_price.ipynb   # Notebook Jupyter (RECOMMANDÉ!)
```

---

## ⏱️ Temps d'Exécution

| Tâche | Temps |
|-------|-------|
| Installation packages | 2-5 min |
| Entraînement modèle | 10-15 min (1x seulement!) |
| Prédiction (1 propriété) | < 1 sec |
| Prédiction (1000 propriétés) | 5-10 sec |

---

## 🎓 Prochaines Étapes

1. ✅ Faire 2-3 prédictions test
2. ✅ Vérifier la précision des résultats
3. ✅ Adapter les données d'entrée à votre cas
4. ✅ Intégrer dans votre application (si besoin)

---

## 📞 Support

**Problème?** Consultez:
1. `README.md` - Documentation complète
2. `docs/guide_utilisation.md` - Guide détaillé
3. `docs/model_card.md` - Détails du modèle

---

## 🎉 C'est tout!

Vous avez maintenant un système de prédiction des prix immobiliers opérationnel! 

**Bon prédiction! 🏠💰**
