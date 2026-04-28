# ImmoPrix — Morocco Real Estate Price Estimator
Created by **Talib Abdeljalil**

AI-powered property price prediction for Morocco. Trained on live Mubawab listings, calibrated with Yakeey district-level reference prices.

**Live demo**: [abdo0.pythonanywhere.com](https://abdo0.pythonanywhere.com) *(deployed via PythonAnywhere)*

---

## Features

- Lightweight, fast prediction engine using Yakeey price/m² reference for 273 districts across 13 cities
- XGBoost model training available for local development and research
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

### Running Locally with XGBoost Enabled

By default, the deployed code bypasses the heavy `xgboost` library to prevent freezing on PythonAnywhere's 512MB free tier. If you are running the project locally and want to use the full trained AI model:

1. Make sure you have installed the full dependencies: `pip install xgboost scikit-learn pandas` (or just use `pip install -r requirements.txt`).
2. Open `src/models/Xgboost/predict.py`.
3. Locate the `__init__` function (around line 176) and **delete** these three lines:
   ```python
   print("[DEPLOY] Bypassing XGBoost to prevent PythonAnywhere memory crashes.")
   self._use_mock()
   return
   ```
4. Restart the Flask app. It will now load and use your trained `.joblib` models!

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
│   │   ├── predict.py                 # Prediction engine (bypasses XGBoost for deployment)
│   │   └── *.joblib                   # Old trained models (kept for reference)
│   ├── pipeline_orchestrator.py       # Full pipeline runner
│   └── webapp/
│       ├── app.py                     # Flask backend
│       ├── templates/index.html       # UI
│       └── static/                    # CSS + JS
├── requirements.txt                   # Full dependencies (includes XGBoost for local use)
├── requirements-deploy.txt            # Deploy-only (lightweight, no ML libraries)
└── README.md
```

---

## How It Works

1. **Data Collection** — Selenium scrapes live listings from Mubawab.ma
2. **Reference Data** — Yakeey.com price/m² by district (273 districts, 13 cities)
3. **Web App** — Flask serves the UI, returns instant JSON predictions via `/api/predict`
4. **Deployment** — The web app uses a memory-efficient Mock Predictor based on Yakeey reference data to fit cleanly within PythonAnywhere's 512MB free tier constraint.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask |
| Scraping | Selenium + BeautifulSoup |
| Reference | Yakeey.com price data |
| Frontend | Vanilla HTML/CSS/JS |
| Deploy | PythonAnywhere |

---

## Authorship
Created by **Talib Abdeljalil**

## License
MIT
