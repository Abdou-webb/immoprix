# ImmoPrix — Moroccan Real Estate Price Estimator

A data analytics project focused on the Moroccan commercial and residential real estate market. It scrapes live property listings, trains a regression model, and serves predictions through a web interface.

## About

This project was built to explore price dynamics in the Moroccan real estate market — a sector with limited transparent data, especially at the neighborhood level. The goal was to build an end-to-end pipeline from raw web data to a usable prediction tool, calibrated against district-level benchmark prices published by [Yakeey](https://yakeey.com).

The tool covers **16 major cities** and **273 districts**, and was primarily tested against apartment and villa listings on Mubawab.ma.

## Pipeline

1. **Scraping** — Collects listings from Mubawab.ma using Selenium and BeautifulSoup (`src/scrap/`).
2. **Preprocessing** — Cleans raw data, handles missing values, removes outliers, and generates synthetic records from Yakeey district references (`src/preprocessing/`).
3. **Training** — Trains an XGBoost regression model on the combined dataset (`src/preprocessing/retrain_models.py`).
4. **Serving** — Flask web app with a form-based interface to query the model (`src/webapp/`).
5. **Orchestration** — A single script to run the full pipeline from scrape to retrain (`src/pipeline_orchestrator.py`).

## Dataset

Training data consists of **13,760 records**:
- ~220 real listings scraped from Mubawab
- ~13,540 synthetic records generated from Yakeey price references for 273 districts

## Features

The model uses 19 input features:

| Type | Features |
|---|---|
| Numerical | `surface`, `rooms`, `bedrooms`, `bathrooms` |
| Categorical (encoded) | `district_encoded`, `city_encoded`, `category_encoded`, `listing_type_encoded` |
| Derived | `amenity_count`, `rooms_per_surface`, `bed_bath_ratio`, `surface_sq` |
| Boolean | `terrace`, `garage`, `elevator`, `concierge`, `pool`, `security`, `garden` |

## Model Performance

**Algorithm:** XGBoost Regressor  
**Hyperparameters:** `n_estimators=400`, `learning_rate=0.05`, `max_depth=5`

| Metric | Score |
|---|---|
| Training R² | 0.964 |
| 5-fold CV R² | 0.934 |

## Setup

```bash
git clone https://github.com/Abdou-webb/immoprix.git
cd immoprix

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run the webapp
python src/webapp/app.py
```

Available at `http://localhost:5000`.

To retrain with fresh scraped data:
```bash
python src/pipeline_orchestrator.py
```

To skip scraping and just retrain from existing data:
```bash
python src/pipeline_orchestrator.py --no-scrape
```

## Project Structure

```
immoprix/
├── data/
│   ├── mubawab_current_listings.csv   # Scraped listings
│   └── yakeey_price_reference.csv     # District benchmark prices
├── src/
│   ├── scrap/                         # Selenium scraper
│   ├── preprocessing/                 # Data cleaning + model retraining
│   ├── models/Xgboost/                # Trained model + prediction logic
│   ├── webapp/                        # Flask app (templates, static, API)
│   └── pipeline_orchestrator.py       # End-to-end pipeline runner
├── requirements.txt
└── requirements-deploy.txt            # Lightweight deps for PythonAnywhere
```

## Deployment Note

The live version on PythonAnywhere uses a simplified lookup method instead of the full XGBoost model due to a 512 MB memory cap. To run the full model locally, see the bypass flag in `src/models/Xgboost/predict.py`.
