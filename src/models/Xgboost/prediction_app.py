"""
Interactive Real Estate Price Prediction Application
User-friendly CLI interface for entering property data and getting price predictions
"""

import sys
from pathlib import Path
from predict import RealEstatePricePredictor, get_example_input
import pandas as pd


class PredictionApp:
    """Interactive prediction application"""
    
    def __init__(self):
        print("\n" + "="*70)
        print("🏠 MOROCCAN REAL ESTATE PRICE PREDICTION SYSTEM 🏠".center(70))
        print("="*70)
        
        try:
            self.predictor = RealEstatePricePredictor()
        except FileNotFoundError as e:
            print(f"\n❌ Error: {e}")
            print("📌 Please train the model first:")
            print("   python train.py")
            sys.exit(1)
    
    def get_user_input(self):
        """Get property data from user interactively"""
        print("\n" + "-"*70)
        print("📝 ENTER PROPERTY DETAILS")
        print("-"*70)
        
        data = {}
        
        # Location
        print("\n🗺️  Location:")
        print("   Format: 'District, City' (e.g., 'Guéliz, Marrakech')")
        data['location'] = input("   Location: ").strip()
        
        # Numeric features
        print("\n📐 Dimensions:")
        try:
            data['surface'] = float(input("   Surface (m²): "))
            data['rooms'] = int(input("   Total Rooms: "))
            data['bedrooms'] = int(input("   Bedrooms: "))
            data['bathrooms'] = int(input("   Bathrooms: "))
        except ValueError:
            print("❌ Invalid input. Please enter numbers only.")
            return None
        
        # Property type
        print("\n🏢 Property Type:")
        print("   Options: Apartment, Villa, House, Other")
        data['property_category'] = input("   Category: ").strip()
        
        # Property listing type
        print("\n💼 Listing Type:")
        print("   Options: For_Sale, For_Rent")
        listing = input("   Type: ").strip()
        if listing in ('For Sale', 'sale', 'vente'):
            listing = 'For_Sale'
        elif listing in ('For Rent', 'rent', 'location'):
            listing = 'For_Rent'
        data['listing_type'] = listing
        
        # Amenities
        print("\n✨ Amenities (yes/no):")
        amenities = ['terrace', 'garage', 'elevator', 'concierge', 'pool', 'security', 'garden']
        for amenity in amenities:
            response = input(f"   {amenity.capitalize()}? (y/n): ").strip().lower()
            data[amenity] = response in ['y', 'yes', '1', 'true']
        
        return data
    
    def validate_input(self, data):
        """Validate input data"""
        if data is None:
            return False
        
        # Check required fields
        required = ['location', 'surface', 'rooms', 'bedrooms', 'bathrooms', 'property_category', 'listing_type']
        for field in required:
            if field not in data or data[field] is None:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate numeric ranges
        if data['surface'] < 10 or data['surface'] > 2000:
            print("❌ Surface must be between 10 and 2000 m²")
            return False
        
        if data['rooms'] < 0 or data['rooms'] > 20:
            print("❌ Rooms must be between 0 and 20")
            return False
        
        if data['bedrooms'] < 0 or data['bedrooms'] > 20:
            print("❌ Bedrooms must be between 0 and 20")
            return False
        
        if data['bathrooms'] < 0 or data['bathrooms'] > 10:
            print("❌ Bathrooms must be between 0 and 10")
            return False
        
        return True
    
    def display_prediction(self, property_data, predicted_price):
        """Display prediction results nicely"""
        print("\n" + "="*70)
        print("📊 PREDICTION RESULTS".center(70))
        print("="*70)
        
        # Display input data
        print("\n🏠 Input Property Details:")
        for key, value in property_data.items():
            if not isinstance(value, bool):
                print(f"   • {key.replace('_', ' ').title()}: {value}")
        
        # Amenities
        amenities = {k: v for k, v in property_data.items() 
                    if k in ['terrace', 'garage', 'elevator', 'concierge', 'pool', 'security', 'garden']}
        amenities_yes = [k for k, v in amenities.items() if v]
        
        if amenities_yes:
            print(f"   • Amenities: {', '.join([a.capitalize() for a in amenities_yes])}")
        else:
            print("   • Amenities: None")
        
        # Prediction
        print("\n" + "-"*70)
        print("💰 PREDICTED PRICE:".ljust(40) + f"{predicted_price:>20,.0f} MAD")
        print("-"*70)
        
        # Additional metrics
        surface = property_data['surface']
        price_per_m2 = predicted_price / surface
        print(f"   Price per m²:".ljust(40) + f"{price_per_m2:>20,.0f} MAD/m²")
        
        # Price range (±10%)
        min_price = predicted_price * 0.9
        max_price = predicted_price * 1.1
        print(f"\n   Estimated Range (±10%):")
        print(f"     Min: {min_price:,.0f} MAD")
        print(f"     Max: {max_price:,.0f} MAD")
        
        print("\n" + "="*70 + "\n")
    
    def run(self):
        """Main application loop"""
        while True:
            print("\n" + "-"*70)
            print("OPTIONS:")
            print("  1. Enter new property manually")
            print("  2. Use example property")
            print("  3. View feature importance")
            print("  4. Exit")
            print("-"*70)
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                property_data = self.get_user_input()
                
                if not self.validate_input(property_data):
                    continue
                
                try:
                    predicted_price = self.predictor.predict_single(property_data)
                    self.display_prediction(property_data, predicted_price)
                except Exception as e:
                    print(f"\n❌ Error during prediction: {e}")
                    print("💡 Tip: Make sure all required fields are filled correctly")
            
            elif choice == '2':
                property_data = get_example_input()
                print("\n✅ Using example property:")
                
                try:
                    predicted_price = self.predictor.predict_single(property_data)
                    self.display_prediction(property_data, predicted_price)
                except Exception as e:
                    print(f"\n❌ Error during prediction: {e}")
            
            elif choice == '3':
                print("\n📈 Model Information:")
                print(f"   Model Type: {self.predictor.model_type}")
                print(f"   Number of Features: {len(self.predictor.feature_names)}")
                print(f"\n   Features: {', '.join(self.predictor.feature_names[:5])}... (+{len(self.predictor.feature_names)-5})")
            
            elif choice == '4':
                print("\n✅ Thank you for using Real Estate Price Predictor!")
                print("📍 For more info, check: README.md")
                break
            
            else:
                print("❌ Invalid option. Please select 1-4.")


if __name__ == "__main__":
    app = PredictionApp()
    app.run()
