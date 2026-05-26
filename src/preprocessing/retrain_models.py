"""
Data Integration & Model Retraining Pipeline
Combines Avito + Mubawab fresh data and retrains models with current prices
"""

import pandas as pd
import numpy as np
import logging
import sys
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import joblib
import re
from typing import Tuple, List

# Windows consoles use CP-1252 which can't encode checkmark chars.
# Wrap stdout in a writer that replaces unknown chars instead of crashing.
_stdout_handler = logging.StreamHandler(sys.stdout)
try:
    import io
    _stdout_handler.stream = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
except AttributeError:
    pass  # If stdout has no .buffer (e.g. IDLE), leave as-is

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_retraining.log', encoding='utf-8'),
        _stdout_handler,
    ]
)
logger = logging.getLogger(__name__)

class DataIntegration:
    """Combines multiple CSV sources and cleans data"""
    
    def __init__(self, data_dir: str = "../../data"):
        self.data_dir = Path(data_dir)
        self.target_features = ["terrace", "garage", "elevator", "concierge", "pool", "security", "garden"]
    
    def load_fresh_data(self) -> pd.DataFrame:
        """Load the current clean scraped data (numeric format).
        The old mubawab_properties.csv / mubawab_rent.csv use string
        price/surface formats and cannot be combined without a separate parser.
        """
        # Priority: use the freshest clean numeric file
        PREFERRED = ['mubawab_current_listings.csv']
        SKIP = {'mubawab_properties_current.csv',   # combined output (avoid circular)
                'mubawab_properties.csv',            # old string-format file
                'mubawab_rent.csv'}                  # old string-format file

        all_data = []
        csv_files = sorted(self.data_dir.glob("*.csv"),
                          key=lambda x: x.stat().st_mtime, reverse=True)

        # Try preferred files first
        for name in PREFERRED:
            path = self.data_dir / name
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    df.columns = [c.lower().strip() for c in df.columns]
                    if all(c in df.columns for c in ['price','surface','location']):
                        all_data.append(df)
                        logger.info(f"[OK] {name}: {len(df)} records")
                except Exception as exc:
                    logger.warning(f"Error loading {name}: {exc}")

        # Fall back to any other clean CSV not in skip list
        if not all_data:
            for csv_file in csv_files:
                if csv_file.name in SKIP or csv_file.name in PREFERRED:
                    continue
                try:
                    df = pd.read_csv(csv_file)
                    df.columns = [c.lower().strip() for c in df.columns]
                    if all(c in df.columns for c in ['price','surface','location']):
                        # Quick check: price should be numeric
                        sample = pd.to_numeric(df['price'].head(5), errors='coerce')
                        if sample.notna().sum() >= 3:
                            all_data.append(df)
                            logger.info(f"[OK] {csv_file.name}: {len(df)} records")
                except Exception as exc:
                    logger.warning(f"Error loading {csv_file.name}: {exc}")

        if not all_data:
            raise ValueError("No valid CSV files found!")

        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"Loaded {len(combined)} total records from {len(all_data)} file(s)")
        return combined

    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate data"""
        logger.info(f"Starting with {len(df)} records")
        
        # Standardize columns
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Handle price
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            # Remove outliers (1st-99th percentile)
            q1, q99 = df['price'].quantile([0.01, 0.99])
            df = df[(df['price'] >= q1) & (df['price'] <= q99)]
            # Reasonable price range
            df = df[(df['price'] >= 50000) & (df['price'] <= 50000000)]
        
        # Handle surface
        if 'surface' in df.columns:
            df['surface'] = pd.to_numeric(df['surface'], errors='coerce')
            # Remove outliers
            q1, q99 = df['surface'].quantile([0.01, 0.99])
            df = df[(df['surface'] >= q1) & (df['surface'] <= q99)]
            # Reasonable surface range
            df = df[(df['surface'] >= 20) & (df['surface'] <= 500)]
        
        # Handle rooms/bedrooms/bathrooms
        for col in ['rooms', 'bedrooms', 'bathrooms']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                df[col] = df[col].clip(0, 20)
        
        # Handle boolean features
        for feature in self.target_features:
            if feature in df.columns:
                df[feature] = df[feature].fillna(False)
                if df[feature].dtype == 'object':
                    df[feature] = df[feature].astype(str).str.lower().isin(['true', '1', 'yes'])
                else:
                    df[feature] = df[feature].astype(bool)
            else:
                df[feature] = False
        
        # Extract city/district from location
        if 'location' in df.columns:
            df['location'] = df['location'].fillna('Unknown')
            # Strip \n and extra whitespace from scraped locations
            df['location'] = df['location'].str.replace(r'\s+', ' ', regex=True).str.strip()
            split_loc = df['location'].str.split(',', n=1, expand=True)
            df['district'] = split_loc[0].fillna('Unknown').str.strip()
            df['city'] = split_loc[1].fillna('Unknown').str.strip() if 1 in split_loc.columns else 'Unknown'
        else:
            df['district'] = 'Unknown'
            df['city'] = 'Unknown'
        
        # Remove rows with missing critical values
        critical_cols = ['price', 'surface']
        df = df.dropna(subset=critical_cols)
        
        # Filter price/surface ratio (sanity check)
        df['price_per_m2'] = df['price'] / df['surface']
        df = df[(df['price_per_m2'] >= 1000) & (df['price_per_m2'] <= 100000)]
        
        # ── Deduplicate: same price + same surface = same listing ────────────
        before = len(df)
        df = df.drop_duplicates(subset=['price', 'surface'], keep='last')
        logger.info(f"Deduplicated: {before} -> {len(df)} unique records")

        logger.info(f"After cleaning: {len(df)} records")
        logger.info(
            f"  Price: {df['price'].min():,.0f} - {df['price'].max():,.0f} MAD | "
            f"  Avg: {df['price'].mean():,.0f} MAD | Surface avg: {df['surface'].mean():.0f} m2"
        )
        return df
    
    def save_cleaned_data(self, df: pd.DataFrame, filename: str = "mubawab_properties_current.csv"):
        """Save cleaned data"""
        output_path = self.data_dir / filename
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"[SAVED] Cleaned data -> {output_path} ({len(df)} records)")
        return output_path


class ModelRetrainer:
    """Retrain models with fresh data"""
    
    def __init__(self, data_dir: str = "../../data", model_dir: str = "../models/Xgboost"):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.target_features = ["terrace", "garage", "elevator", "concierge", "pool", "security", "garden"]
    
    def prepare_features(self, df: pd.DataFrame):
        """Prepare features — NO data leakage."""
        amenity_cols = self.target_features

        # ── Split location into district / city ──────────────────────────────
        if 'district' not in df.columns or 'city' not in df.columns:
            loc = df.get('location', pd.Series(['Unknown'] * len(df))).astype(str)
            split = loc.str.split(',', n=1, expand=True)
            df['district'] = split[0].str.strip().str.split('\n').str[0].str.strip()
            df['city']     = split[1].str.strip().str.split('\n').str[0].str.strip() if split.shape[1] > 1 else 'Unknown'

        # ── Fill missing columns ─────────────────────────────────────────────
        for col in ['surface', 'rooms', 'bedrooms', 'bathrooms']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)
        for col in amenity_cols:
            if col not in df.columns:
                df[col] = False
            df[col] = df[col].astype(int)

        # ── Encode location ──────────────────────────────────────────────────
        le_district = LabelEncoder()
        le_city     = LabelEncoder()
        df['district_encoded'] = le_district.fit_transform(df['district'].fillna('Unknown'))
        df['city_encoded']     = le_city.fit_transform(df['city'].fillna('Unknown'))

        # ── Encode property category (apartment / villa / etc.) ─────────────
        le_cat = LabelEncoder()
        cat_col = df.get('property_category', pd.Series(['Apartment'] * len(df))).fillna('Apartment')
        df['category_encoded'] = le_cat.fit_transform(cat_col)

        # ── Encode listing type (For Sale / For Rent) ────────────────────────
        le_type = LabelEncoder()
        type_col = df.get('type', pd.Series(['For_Sale'] * len(df))).fillna('For_Sale')
        df['listing_type_encoded'] = le_type.fit_transform(type_col)

        # ── Engineered features (no leakage) ────────────────────────────────
        df['amenity_count']    = df[amenity_cols].sum(axis=1)
        df['rooms_per_surface'] = df['rooms'] / df['surface'].clip(lower=1)
        df['bed_bath_ratio']   = df['bedrooms'] / (df['bathrooms'].clip(lower=1))
        df['surface_sq']       = df['surface'] ** 2

        feature_cols = [
            'surface', 'rooms', 'bedrooms', 'bathrooms',
            'district_encoded', 'city_encoded',
            'category_encoded', 'listing_type_encoded',
            'amenity_count', 'rooms_per_surface',
            'bed_bath_ratio', 'surface_sq',
        ] + amenity_cols

        X = df[feature_cols].values.astype(float)
        y = df['price'].values.astype(float)

        logger.info(
            f"Features ({len(feature_cols)}): {feature_cols}\n"
            f"  Samples: {len(X)} | Price mean: {y.mean():,.0f} MAD | std: {y.std():,.0f} MAD"
        )
        return X, y, feature_cols, {
            'district': le_district, 'city': le_city,
            'property_category': le_cat, 'listing_type': le_type,
        }
    
    def train_model(self, X: np.ndarray, y: np.ndarray):
        """Train XGBoost model (better accuracy on small datasets)."""
        try:
            from xgboost import XGBRegressor
            model = XGBRegressor(
                n_estimators=400,
                learning_rate=0.05,
                max_depth=5,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=3,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                verbosity=0,
            )
            model_name = 'XGBoost'
        except ImportError:
            model = GradientBoostingRegressor(
                n_estimators=300, learning_rate=0.05,
                max_depth=4, min_samples_split=5,
                min_samples_leaf=3, subsample=0.8,
                random_state=42, verbose=0,
            )
            model_name = 'GradientBoosting'

        from sklearn.model_selection import cross_val_score, KFold
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='r2')
        logger.info(f"{model_name} CV R2: {cv_scores.round(3)} | Mean: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

        model.fit(X, y)
        train_r2 = model.score(X, y)
        logger.info(f"Training R2: {train_r2:.4f}")
        return model
    
    def save_model(
        self,
        model,
        feature_cols: list,
        encoders: dict,
        scaler=None,
        listing_type: str = "For Sale",
    ):
        """Save trained model in the portable JSON format expected by predict.py."""
        import json
        
        # Save XGBoost model to JSON
        model_path = self.model_dir / "model_xgb.json"
        model.save_model(model_path)
        
        # Convert encoders to class lists
        enc_dict = {}
        for k, v in encoders.items():
            enc_dict[k] = list(v.classes_)
            
        # Scaler
        scaler_dict = None
        if scaler is not None:
            scaler_dict = {
                'mean': scaler.mean_.tolist(),
                'scale': scaler.scale_.tolist()
            }
            
        meta = {
            'features': feature_cols,
            'type': listing_type,
            'encoders': enc_dict,
            'scaler': scaler_dict,
            'trained_at': datetime.now().isoformat(),
            'n_features': len(feature_cols),
        }
        
        meta_path = self.model_dir / "model_meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
            
        logger.info(f"[SAVED] Portable Model -> {model_path}")
        logger.info(f"[SAVED] Meta -> {meta_path}")
        return model_path
    
    def generate_synthetic_data(self) -> pd.DataFrame:
        """Generate synthetic listings based on Yakeey reference data to enrich XGBoost."""
        import random
        yakeey_path = self.data_dir / 'yakeey_price_reference.csv'
        if not yakeey_path.exists():
            logger.warning("Yakeey reference not found. Skipping synthetic data.")
            return pd.DataFrame()
        
        ref_df = pd.read_csv(yakeey_path)
        synthetic_rows = []
        
        for _, row in ref_df.iterrows():
            city = str(row.get('city', '')).strip()
            district = str(row.get('district', '')).strip()
            if not city or not district:
                continue
                
            apt_price_m2 = pd.to_numeric(row.get('apartment_price_m2'), errors='coerce')
            villa_price_m2 = pd.to_numeric(row.get('villa_price_m2'), errors='coerce')
            
            # Generate 40 apartments per district
            if pd.notna(apt_price_m2) and apt_price_m2 > 0:
                for _ in range(40):
                    surface = random.randint(40, 200)
                    rooms = max(1, int(surface / 30)) + random.randint(0, 1)
                    bedrooms = max(1, rooms - 1)
                    bathrooms = 1 if surface < 80 else random.randint(1, 2)
                    
                    # Amenities
                    terrace = random.choice([0, 1])
                    elevator = random.choice([0, 1]) if surface > 60 else 0
                    garage = random.choice([0, 1])
                    concierge = random.choice([0, 1])
                    pool = random.choice([0, 1]) if surface > 120 else 0
                    security = random.choice([0, 1])
                    garden = 0
                    
                    # Base price
                    base_price = surface * apt_price_m2
                    amenity_bonus = (terrace + garage + elevator + pool + security + concierge + garden) * surface * 300
                    final_price = (base_price + amenity_bonus) * random.uniform(0.9, 1.1)
                    
                    synthetic_rows.append({
                        'city': city, 'district': district, 'location': f"{district}, {city}",
                        'surface': surface, 'rooms': rooms, 'bedrooms': bedrooms, 'bathrooms': bathrooms,
                        'property_category': 'Apartment', 'type': 'For Sale', 'price': final_price,
                        'terrace': terrace, 'garage': garage, 'elevator': elevator, 'concierge': concierge,
                        'pool': pool, 'security': security, 'garden': garden
                    })
            
            # Generate 15 villas per district
            if pd.notna(villa_price_m2) and villa_price_m2 > 0:
                for _ in range(15):
                    surface = random.randint(200, 600)
                    rooms = max(3, int(surface / 60)) + random.randint(0, 2)
                    bedrooms = max(2, rooms - 1)
                    bathrooms = random.randint(2, 4)
                    
                    # Base price
                    base_price = surface * villa_price_m2 * 1.3 # Category multiplier
                    amenity_bonus = surface * 300 * 5 # assume 5 amenities on avg
                    final_price = (base_price + amenity_bonus) * random.uniform(0.9, 1.1)
                    
                    synthetic_rows.append({
                        'city': city, 'district': district, 'location': f"{district}, {city}",
                        'surface': surface, 'rooms': rooms, 'bedrooms': bedrooms, 'bathrooms': bathrooms,
                        'property_category': 'Villa', 'type': 'For Sale', 'price': final_price,
                        'terrace': 1, 'garage': 1, 'elevator': 0, 'concierge': 1,
                        'pool': random.choice([0, 1]), 'security': 1, 'garden': 1
                    })
                    
        synth_df = pd.DataFrame(synthetic_rows)
        logger.info(f"Generated {len(synth_df)} synthetic listings from Yakeey reference.")
        return synth_df
    
    def run(self, csv_file: str = "mubawab_properties_current.csv"):
        """Full retraining pipeline"""
        try:
            # Load data
            data_path = self.data_dir / csv_file
            if not data_path.exists():
                raise FileNotFoundError(f"Data file not found: {data_path}")
            
            logger.info(f"Loading data from {data_path}")
            df_real = pd.read_csv(data_path)
            
            # Inject synthetic data
            df_synth = self.generate_synthetic_data()
            if not df_synth.empty:
                df = pd.concat([df_real, df_synth], ignore_index=True)
                logger.info(f"Combined {len(df_real)} real listings with {len(df_synth)} synthetic listings.")
            else:
                df = df_real

            # Prepare features
            X, y, feature_cols, encoders = self.prepare_features(df)

            # Train model
            model = self.train_model(X, y)

            # Save model bundle (portable format)
            self.save_model(
                model,
                feature_cols=feature_cols,
                encoders=encoders,
                listing_type="For Sale",
            )
            
            logger.info(
                f"\n[COMPLETED] MODEL RETRAINING\n"
                f"Dataset: Fresh Avito + Mubawab 2024/2025\n"
                f"Samples: {len(X)}\n"
                f"Training R2: {model.score(X, y):.4f}\n"
                f"Status: Ready for prediction\n"
            )
            
            return model
            
        except Exception as e:
            logger.error(f"Error in retraining: {e}", exc_info=True)
            raise


def main():
    """Main execution"""
    logger.info("="*50)
    logger.info("REAL ESTATE DATA & MODEL RETRAINING PIPELINE")
    logger.info("="*50)
    
    try:
        # Step 1: Retrain models using existing cleaned dataset + synthetic data
        logger.info("\n[Step 1] Retraining models with current prices + synthetic Yakeey data...")
        retrainer = ModelRetrainer(data_dir="data", model_dir="src/models/Xgboost")
        model = retrainer.run(csv_file="mubawab_current_listings.csv")
        
        logger.info("\n" + "="*50)
        logger.info("[OK] PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("="*50)
        logger.info("\nNext steps:")
        logger.info("1. Test predictions with prediction_app.py")
        logger.info("2. Validate against known property prices")
        logger.info("3. Adjust model hyperparameters if needed")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
