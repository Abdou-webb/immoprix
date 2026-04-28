"""
Real Estate Price Prediction Module — 2026 Edition
Loads trained model and predicts property prices.
Calibrated with Yakeey market reference prices per m² by district.
"""

import numpy as np
import os
import csv
import json
from pathlib import Path
from difflib import SequenceMatcher

try:
    import joblib
except ImportError:
    joblib = None


# ── Lightweight replacements for sklearn (no version dependency) ──────────────

class _SimpleScaler:
    """Drop-in replacement for StandardScaler.transform() using saved params."""
    def __init__(self, mean, scale):
        self.mean_ = np.array(mean)
        self.scale_ = np.array(scale)

    def transform(self, X):
        return (np.array(X) - self.mean_) / self.scale_


class _SimpleEncoder:
    """Drop-in replacement for LabelEncoder.transform() using saved class list."""
    def __init__(self, classes):
        self.classes_ = classes
        self._map = {c: i for i, c in enumerate(classes)}

    def transform(self, values):
        return [self._map.get(v, 0) for v in values]

# ── Yakeey Market Reference ───────────────────────────────────────────────────

class MarketReference:
    """Loads Yakeey price/m² reference data and provides fuzzy-matched lookups."""

    def __init__(self, csv_path=None):
        self.data = {}  # {(city_lower, district_lower): {'apartment': X, 'villa': Y}}
        self.city_averages = {}  # {city_lower: avg_price_m2}

        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent.parent / "data" / "yakeey_price_reference.csv"

        if not csv_path.exists():
            print(f"[REF] No Yakeey reference file found at {csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                city_totals = {}
                for row in reader:
                    city = row['city'].strip().lower()
                    district = row['district'].strip().lower()
                    apt = float(row['apartment_price_m2']) if row['apartment_price_m2'].strip() else None
                    villa = float(row['villa_price_m2']) if row['villa_price_m2'].strip() else None
                    self.data[(city, district)] = {'apartment': apt, 'villa': villa}

                    # Track city averages
                    price = apt or villa
                    if price:
                        city_totals.setdefault(city, []).append(price)

                for city, prices in city_totals.items():
                    self.city_averages[city] = np.mean(prices)

            print(f"[REF] Loaded {len(self.data)} district prices, {len(self.city_averages)} cities")
        except Exception as e:
            print(f"[REF] Error loading reference: {e}")

    def _fuzzy_find(self, city: str, district: str, threshold=0.55):
        """Find the closest matching district name using fuzzy matching."""
        city_l = city.lower().strip()
        district_l = district.lower().strip()

        # 1. Exact match
        key = (city_l, district_l)
        if key in self.data:
            return self.data[key]

        # 2. Substring match (e.g., "Anfa" matches "Anfa Superieur")
        candidates = [(k, v) for k, v in self.data.items() if k[0] == city_l]
        for (c, d), v in candidates:
            if district_l in d or d in district_l:
                return v

        # 3. Fuzzy match
        best_score = 0
        best_val = None
        for (c, d), v in candidates:
            score = SequenceMatcher(None, district_l, d).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_val = v

        return best_val

    def get_price_m2(self, city: str, district: str, property_type: str = 'apartment') -> float:
        """Get price per m² for a given city/district/type. Returns 0 if not found."""
        entry = self._fuzzy_find(city, district)
        if entry is None:
            return 0

        ptype = property_type.lower()
        if ptype in ('villa', 'house', 'riad'):
            return entry.get('villa') or entry.get('apartment') or 0
        return entry.get('apartment') or entry.get('villa') or 0

    def get_city_avg(self, city: str) -> float:
        """Get city-level average price/m²."""
        return self.city_averages.get(city.lower().strip(), 0)


# ── Mock Predictor (fallback) ─────────────────────────────────────────────────

class MockPredictor:
    """Heuristic fallback when no trained model is available."""

    def __init__(self, market_ref=None):
        self.market_ref = market_ref or MarketReference()
        self.CITY_PRICES = {
            'casablanca': 14000, 'rabat': 12000, 'marrakech': 11000,
            'agadir': 10000, 'tanger': 10000, 'fes': 5500,
            'meknes': 5000, 'oujda': 5000, 'kenitra': 6000,
            'sale': 8000, 'temara': 8000, 'mohammedia': 10000,
            'el jadida': 6000, 'bouskoura': 10000, 'tetouan': 7000,
        }
        self.CATEGORY_MULT = {'villa': 1.3, 'house': 1.2, 'apartment': 1.0, 'studio': 0.75}

    def predict_single(self, d):
        location = str(d.get('location', d.get('city', '')))
        parts = location.split(',', 1)
        district = parts[0].strip()
        city = parts[1].strip() if len(parts) > 1 else district

        surface = float(d.get('surface', 80) or 80)
        cat = str(d.get('property_category', 'Apartment')).lower()
        listing = str(d.get('listing_type', 'For_Sale'))

        # Try Yakeey reference first
        ref_price = self.market_ref.get_price_m2(city, district, cat)
        if ref_price > 0:
            ppm2 = ref_price
        else:
            city_avg = self.market_ref.get_city_avg(city)
            ppm2 = city_avg if city_avg > 0 else self.CITY_PRICES.get(city.lower(), 10000)

        mult = self.CATEGORY_MULT.get(cat, 1.0)
        rent_factor = 0.005 if 'rent' in listing.lower() else 1.0

        amenities = ['terrace','garage','elevator','pool','security','garden','concierge']
        amenity_bonus = sum(d.get(a, False) for a in amenities) * surface * 300

        return (ppm2 * surface * mult + amenity_bonus) * rent_factor


# ── Main Predictor ────────────────────────────────────────────────────────────

class RealEstatePricePredictor:
    """Loads a trained model bundle and predicts property prices,
    calibrated with Yakeey market reference data."""

    def __init__(self, model_path=None):
        # Load market reference data
        self.market_ref = MarketReference()
        
        # [PythonAnywhere Fix] 
        # XGBoost consumes too much memory for the free tier and causes the WSGI server to hang/deadlock.
        # We bypass it and use the calibrated MockPredictor which uses the Yakeey reference data directly.
        print("[DEPLOY] Bypassing XGBoost to prevent PythonAnywhere memory crashes.")
        self._use_mock()
        return

        if xgb_json.exists() and meta_json.exists():
            self._load_portable(xgb_json, meta_json)
            return

        # Fallback to .joblib
        if model_path is None:
            files = list(model_dir.glob("real_estate_model_*.joblib"))
            if not files:
                print("[DEMO] No trained model found. Using market-reference predictions.")
                self._use_mock()
                return
            model_path = max(files, key=os.path.getctime)
            print(f"[MODEL] Found: {model_path.name}")

        loaded = joblib.load(model_path)
        self.is_mock = False
        self.mock_predictor = MockPredictor(self.market_ref)

        if isinstance(loaded, dict):
            self.model         = loaded['model']
            self.scaler        = loaded.get('scaler')
            self.feature_names = loaded.get('features', [])
            self.model_type    = loaded.get('type', 'For Sale')
            self.encoders      = loaded.get('encoders', {})
            trained_at         = loaded.get('trained_at', 'unknown')
            print(f"[OK] Model: {self.model_type} | {len(self.feature_names)} features | trained {trained_at}")
        else:
            print("[!] Legacy raw model — using heuristics for missing features.")
            self.model         = loaded
            self.scaler        = None
            self.encoders      = {}
            self.model_type    = "For Sale"
            self.feature_names = [
                'surface','rooms','bedrooms','bathrooms',
                'district_encoded','city_encoded',
                'category_encoded','listing_type_encoded',
                'amenity_count','rooms_per_surface',
                'bed_bath_ratio','surface_sq',
                'terrace','garage','elevator','concierge','pool','security','garden',
            ]

    def _load_portable(self, xgb_path, meta_path):
        """Load from portable XGBoost JSON + metadata JSON (no numpy/sklearn version deps)."""
        import xgboost as xgb
        import json

        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        booster = xgb.XGBRegressor()
        booster.load_model(str(xgb_path))

        self.model = booster
        self.is_mock = False
        self.mock_predictor = MockPredictor(self.market_ref)
        self.feature_names = meta.get('features', [])
        self.model_type = meta.get('type', 'For Sale')

        # Rebuild scaler from saved params
        scaler_data = meta.get('scaler')
        if scaler_data:
            self.scaler = _SimpleScaler(scaler_data['mean'], scaler_data['scale'])
        else:
            self.scaler = None

        # Rebuild encoders from saved class lists
        enc_data = meta.get('encoders', {})
        self.encoders = {}
        for name, classes in enc_data.items():
            self.encoders[name] = _SimpleEncoder(classes)

        trained_at = meta.get('trained_at', 'unknown')
        print(f"[OK] Portable model: {self.model_type} | {len(self.feature_names)} features | trained {trained_at}")

    def _use_mock(self):
        self.is_mock        = True
        self.mock_predictor = MockPredictor(self.market_ref)
        self.feature_names  = []
        self.model_type     = "Demo"
        self.encoders       = {}

    # ------------------------------------------------------------------
    def predict_single(self, property_data: dict) -> float:
        if self.is_mock:
            return self.mock_predictor.predict_single(property_data)

        try:
            surface   = float(property_data.get('surface', 80) or 80)
            rooms     = int(property_data.get('rooms', 3) or 3)
            bedrooms  = int(property_data.get('bedrooms', 2) or 2)
            bathrooms = int(property_data.get('bathrooms', 1) or 1)

            # Location
            location     = str(property_data.get('location', 'Unknown'))
            parts        = location.split(',', 1)
            district_raw = parts[0].strip() if parts else 'Unknown'
            city_raw     = parts[1].strip() if len(parts) > 1 else 'Unknown'

            # Category & listing type
            category_raw     = str(property_data.get('property_category', 'Apartment') or 'Apartment')
            listing_type_raw = str(property_data.get('listing_type', 'For_Sale') or 'For_Sale')
            if listing_type_raw in ('For Sale', 'sale', 'vente'):
                listing_type_raw = 'For_Sale'
            if listing_type_raw in ('For Rent', 'rent', 'location'):
                listing_type_raw = 'For_Rent'

            def safe_encode(le, val):
                if le is None: return 0
                try:   return int(le.transform([val])[0])
                except ValueError: return 0

            enc = self.encoders
            district_enc     = safe_encode(enc.get('district'), district_raw)
            city_enc         = safe_encode(enc.get('city'), city_raw)
            category_enc     = safe_encode(enc.get('property_category'), category_raw)
            listing_type_enc = safe_encode(enc.get('listing_type'), listing_type_raw)

            amenity_keys  = ['terrace','garage','elevator','concierge','pool','security','garden']
            amenity_vals  = {k: int(bool(property_data.get(k, False))) for k in amenity_keys}
            amenity_count = sum(amenity_vals.values())

            row = {
                'surface':               surface,
                'rooms':                 rooms,
                'bedrooms':              bedrooms,
                'bathrooms':             bathrooms,
                'district_encoded':      district_enc,
                'city_encoded':          city_enc,
                'category_encoded':      category_enc,
                'listing_type_encoded':  listing_type_enc,
                'amenity_count':         amenity_count,
                'rooms_per_surface':     rooms / max(surface, 1),
                'bed_bath_ratio':        bedrooms / max(bathrooms, 1),
                'surface_sq':            surface ** 2,
                **amenity_vals,
            }

            # Build feature array directly without pandas
            X_row = [row.get(feat, 0) for feat in self.feature_names]
            X = np.array([X_row], dtype=float)

            if self.scaler is not None:
                X = self.scaler.transform(X)

            model_price = float(self.model.predict(X)[0])

            # ── Calibrate with Yakeey market reference ──
            ref_price_m2 = self.market_ref.get_price_m2(city_raw, district_raw, category_raw)

            if ref_price_m2 > 0:
                is_rent = 'rent' in listing_type_raw.lower()
                if is_rent:
                    # For rent: reference is sale price, convert to monthly rent (~0.4-0.6% of sale price)
                    market_based = ref_price_m2 * surface * 0.005
                else:
                    market_based = ref_price_m2 * surface

                # Blend: 70% market reference, 30% model prediction
                # This anchors the prediction to real district prices
                blended_price = 0.70 * market_based + 0.30 * model_price

                # Apply amenity premium on top (±1-3% per amenity)
                amenity_premium = 1.0 + (amenity_count * 0.015)
                final_price = blended_price * amenity_premium
            else:
                # No market reference found — use city average for sanity check
                city_avg = self.market_ref.get_city_avg(city_raw)
                if city_avg > 0:
                    is_rent = 'rent' in listing_type_raw.lower()
                    if is_rent:
                        market_based = city_avg * surface * 0.005
                    else:
                        market_based = city_avg * surface
                    # Lighter blend when only city-level data available
                    final_price = 0.40 * market_based + 0.60 * model_price
                else:
                    final_price = model_price

            return max(final_price, 0)

        except Exception as exc:
            print(f"[!] Prediction error: {exc}. Falling back to demo mode.")
            return self.mock_predictor.predict_single(property_data)

    def predict_batch(self, properties: list) -> list:
        return [self.predict_single(p) for p in properties]


def get_example_input() -> dict:
    """Return a realistic example property for quick testing."""
    return {
        'location': 'Anfa, Casablanca',
        'surface': 120,
        'rooms': 4,
        'bedrooms': 3,
        'bathrooms': 2,
        'property_category': 'Apartment',
        'listing_type': 'For_Sale',
        'terrace': True,
        'garage': True,
        'elevator': True,
        'concierge': False,
        'pool': False,
        'security': True,
        'garden': False,
    }


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    predictor = RealEstatePricePredictor()
    examples = [
        {"location": "Anfa, Casablanca",    "surface": 120, "rooms": 4, "bedrooms": 3,
         "bathrooms": 2, "property_category": "Apartment", "listing_type": "For_Sale",
         "garage": True, "elevator": True},
        {"location": "Gauthier, Casablanca", "surface": 90,  "rooms": 3, "bedrooms": 2,
         "bathrooms": 2, "property_category": "Apartment", "listing_type": "For_Sale",
         "garage": True, "elevator": True},
        {"location": "Gueliz, Marrakech",   "surface": 90,  "rooms": 3, "bedrooms": 2,
         "bathrooms": 1, "property_category": "Apartment", "listing_type": "For_Sale",
         "terrace": True},
        {"location": "Hassan, Rabat",       "surface": 150, "rooms": 5, "bedrooms": 4,
         "bathrooms": 2, "property_category": "Villa", "listing_type": "For_Sale",
         "garage": True, "pool": True},
        {"location": "Maarif, Casablanca",  "surface": 80,  "rooms": 3, "bedrooms": 2,
         "bathrooms": 1, "property_category": "Apartment", "listing_type": "For_Sale"},
        {"location": "Ville Verte, Bouskoura", "surface": 140, "rooms": 4, "bedrooms": 3,
         "bathrooms": 2, "property_category": "Apartment", "listing_type": "For_Sale",
         "garage": True, "pool": True, "security": True},
    ]
    print("\n" + "="*60)
    for ex in examples:
        price = predictor.predict_single(ex)
        print(f"  {ex['location']} | {ex['surface']}m2 | {ex['property_category']}")
        print(f"  => {price:,.0f} MAD  ({price/ex['surface']:,.0f} MAD/m2)\n")
    print("="*60)
