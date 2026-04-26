# ImmoPrix — Morocco Real Estate Price Estimator

AI-powered property price prediction for Morocco. Trained on live Mubawab listings, calibrated with Yakeey district-level reference prices.

**Live demo**: [immoprix.onrender.com](https://immoprix.onrender.com) *(deploy via Render)*

---

## Features

- XGBoost model trained on scraped Mubawab data (2026)
- Calibrated with Yakeey price/m² reference for 273 districts across 13 cities
- Flask web interface with instant predictions
- Fuzzy district name matching for robust lookups
- For Sale & For Rent support

---

## Quick Start

```bash
# Clone
git clone https://github.com/Abdou-webb/immoprix.git
cd immoprix

# Setup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Run
python src/webapp/app.py
```

Open [http://localhost:5000](http://localhost:5000)

---

## Project Structure

```
immoprix/
├── data/
│   ├── mubawab_current_listings.csv   # Scraped training data
│   └── yakeey_price_reference.csv     # District price/m² reference
├── src/
│   ├── scrap/                         # Selenium scrapers
│   │   └── mubawab_scraper_modern.py
│   ├── preprocessing/
│   │   └── retrain_models.py          # Data cleaning + model training
│   ├── models/Xgboost/
│   │   ├── predict.py                 # Prediction engine + Yakeey calibration
│   │   └── *.joblib                   # Trained models
│   ├── pipeline_orchestrator.py       # Full pipeline runner
│   └── webapp/
│       ├── app.py                     # Flask backend
│       ├── templates/index.html       # UI
│       └── static/                    # CSS + JS
├── requirements.txt                   # Full dependencies
├── requirements-deploy.txt            # Deploy-only (no selenium)
├── Procfile                           # Render/Heroku start command
└── render.yaml                        # Render.com auto-config
```

---

## How It Works

1. **Data Collection** — Selenium scrapes live listings from Mubawab.ma
2. **Reference Data** — Yakeey.com price/m² by district (273 districts, 13 cities)
3. **Model** — XGBoost trained on cleaned listings with feature engineering
4. **Calibration** — Predictions are blended: 70% Yakeey market reference + 30% XGBoost model
5. **Web App** — Flask serves the UI, returns instant JSON predictions via `/api/predict`

---

## API

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Casablanca",
    "district": "Anfa",
    "surface": 120,
    "rooms": 4,
    "bedrooms": 3,
    "bathrooms": 2,
    "property_category": "Apartment",
    "listing_type": "For_Sale",
    "garage": true,
    "elevator": true
  }'
```

Response:
```json
{
  "predicted_price": 2076778,
  "price_per_m2": 17306,
  "min_price": 1869100,
  "max_price": 2284456,
  "confidence": 92
}
```

---

## Deploy

### Render (free)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service → connect repo
3. Render auto-detects `render.yaml` — click Deploy
4. Live at `https://immoprix.onrender.com`

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Model | XGBoost |
| Backend | Flask |
| Scraping | Selenium + BeautifulSoup |
| Reference | Yakeey.com price data |
| Frontend | Vanilla HTML/CSS/JS |
| Deploy | Render / Gunicorn |

---

## License

MIT
