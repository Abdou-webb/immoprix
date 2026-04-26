"""
Real Estate Price Prediction - Flask Web Application
Mubawab-inspired UI with 2026 market data + Yakeey calibration
"""

import sys
import os
import csv
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src" / "models" / "Xgboost"))

from predict import RealEstatePricePredictor

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

@app.template_filter('format_number')
def format_number(value):
    try:    return f"{int(value):,}"
    except: return value


# ── Predictor ──────────────────────────────────────────────────────────────────
predictor = RealEstatePricePredictor()


# ── Config ─────────────────────────────────────────────────────────────────────
def load_districts_from_yakeey():
    """Build district lists per city from Yakeey reference CSV."""
    districts = {}
    ref_path = ROOT / "data" / "yakeey_price_reference.csv"
    if not ref_path.exists():
        return districts

    try:
        with open(ref_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = row['city'].strip()
                district = row['district'].strip()
                districts.setdefault(city, []).append(district)
        # Deduplicate and sort
        for city in districts:
            districts[city] = sorted(set(districts[city]))
    except Exception as e:
        print(f"[WARN] Could not load districts: {e}")

    return districts

DISTRICTS = load_districts_from_yakeey()
CITIES = sorted(DISTRICTS.keys()) if DISTRICTS else [
    "Casablanca", "Rabat", "Marrakech", "Agadir", "Fes", "Tanger",
    "Meknes", "Oujda", "Kenitra", "Tetouan", "Sale", "Bouskoura",
    "El Jadida", "Mohammedia", "Temara",
]

# Add any missing cities
for c in ["Ifrane", "Essaouira", "Nador"]:
    if c not in CITIES:
        CITIES.append(c)
CITIES.sort()

PROPERTY_CATEGORIES = ["Apartment", "Villa", "House", "Studio", "Riad", "Penthouse", "Duplex"]

# Count total districts for stats
total_districts = sum(len(d) for d in DISTRICTS.values())
MARKET_STATS = {
    "avg_price":      1_752_000,
    "avg_price_m2":   14_000,
    "total_listings": total_districts or 273,
    "cities":         len(CITIES),
}


# ── Prediction ─────────────────────────────────────────────────────────────────

def predict_price(form_data: dict) -> dict:
    try:
        surface   = float(form_data.get("surface", 80) or 80)
        rooms     = int(form_data.get("rooms", 3) or 3)
        bedrooms  = int(form_data.get("bedrooms", 2) or 2)
        bathrooms = int(form_data.get("bathrooms", 1) or 1)

        district_raw     = str(form_data.get("district", "Unknown")).strip()
        city_raw         = str(form_data.get("city", "Unknown")).strip()
        location         = f"{district_raw}, {city_raw}"
        category_raw     = str(form_data.get("property_category", "Apartment") or "Apartment")
        listing_type_raw = str(form_data.get("listing_type", "For_Sale") or "For_Sale")
        if listing_type_raw in ("For Sale", "sale"): listing_type_raw = "For_Sale"
        if listing_type_raw in ("For Rent", "rent"): listing_type_raw = "For_Rent"

        amenity_keys  = ["terrace","garage","elevator","concierge","pool","security","garden"]

        prop = {
            'location': location,
            'surface': surface,
            'rooms': rooms,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'property_category': category_raw,
            'listing_type': listing_type_raw,
        }
        # Pass amenities
        for k in amenity_keys:
            prop[k] = bool(form_data.get(k, False))

        predicted = predictor.predict_single(prop)
        ppm2      = predicted / surface if surface > 0 else 0

        # Get reference price for confidence calculation
        ref_price = 0
        if hasattr(predictor, 'market_ref'):
            ref_price = predictor.market_ref.get_price_m2(city_raw, district_raw, category_raw)

        # Confidence: higher when we have Yakeey data for the district
        confidence = 92 if ref_price > 0 else 78

        unit = "/mo" if "rent" in listing_type_raw.lower() else ""
        return {
            "predicted_price": round(predicted),
            "price_per_m2":    round(ppm2),
            "min_price":       round(predicted * 0.90),
            "max_price":       round(predicted * 1.10),
            "location":        location,
            "surface":         surface,
            "listing_type":    listing_type_raw,
            "unit":            unit,
            "confidence":      confidence,
        }

    except Exception as exc:
        return {"error": str(exc)}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           cities=CITIES,
                           districts=DISTRICTS,
                           property_categories=PROPERTY_CATEGORIES,
                           stats=MARKET_STATS)


@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(silent=True) or request.form.to_dict()
    for key in ["terrace","garage","elevator","concierge","pool","security","garden"]:
        val = data.get(key, False)
        data[key] = val in [True, "true", "True", "1", 1, "on"]
    result = predict_price(data)
    return jsonify(result)


@app.route("/api/districts/<city>")
def api_districts(city):
    return jsonify(DISTRICTS.get(city, []))


@app.route("/api/stats")
def api_stats():
    return jsonify(MARKET_STATS)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "="*55)
    print("  Real Estate Price Predictor - 2026 Edition")
    print(f"  {len(DISTRICTS)} cities, {total_districts} districts loaded")
    print(f"  http://localhost:{port}")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)

