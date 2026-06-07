import subprocess
import sys
import logging
from pathlib import Path
from datetime import datetime
import time
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline_execution.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, project_root: str = ".."):
        self.project_root = Path(project_root).resolve()
        self.data_dir = self.project_root / "data"
        self.src_dir = self.project_root / "src"
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        self.execution_report = {
            'start_time': datetime.now().isoformat(),
            'steps': {},
            'total_properties_scraped': 0,
            'model_metrics': {}
        }
    
    def log_section(self, title: str):
        logger.info("\n" + "="*70)
        logger.info(f"  {title}")
        logger.info("="*70)
    
    def step_scrape_mubawab(self, max_pages: int = 5, timeout: int = 3600):
        self.log_section("STEP 1: SCRAPING MUBAWAB")
        try:
            script_path = self.src_dir / "scrap" / "mubawab_scraper_modern.py"
            
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace("MAX_PAGES = 5", f"MAX_PAGES = {max_pages}")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=self.src_dir / "scrap",
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.execution_report['steps']['mubawab_scraping'] = 'success'
                return True
            else:
                self.execution_report['steps']['mubawab_scraping'] = 'failed'
                return False
                
        except subprocess.TimeoutExpired:
            self.execution_report['steps']['mubawab_scraping'] = 'timeout'
            return False
        except Exception as e:
            self.execution_report['steps']['mubawab_scraping'] = f'error: {str(e)}'
            return False
    
    def step_scrape_avito(self, timeout: int = 1800):
        self.log_section("STEP 2: SCRAPING AVITO")
        try:
            scrapy_dir = self.src_dir / "scrap" / "scrapping"
            
            result = subprocess.run(
                [sys.executable, "-m", "scrapy", "crawl", "avito", "-O", 
                 str(self.data_dir / "avito_current.csv")],
                cwd=str(scrapy_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.execution_report['steps']['avito_scraping'] = 'success'
                return True
            else:
                self.execution_report['steps']['avito_scraping'] = 'skipped'
                return False
                
        except subprocess.TimeoutExpired:
            self.execution_report['steps']['avito_scraping'] = 'timeout'
            return False
        except Exception as e:
            self.execution_report['steps']['avito_scraping'] = f'skipped: {str(e)}'
            return False
    
    def step_consolidate_data(self):
        self.log_section("STEP 3: DATA CONSOLIDATION & CLEANING")
        try:
            script_path = self.src_dir / "preprocessing" / "retrain_models.py"
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                self.execution_report['steps']['data_consolidation'] = 'success'
                return True
            else:
                self.execution_report['steps']['data_consolidation'] = 'failed'
                return False
                
        except Exception as e:
            self.execution_report['steps']['data_consolidation'] = f'error: {str(e)}'
            return False
    
    def step_retrain_models(self):
        self.log_section("STEP 4: MODEL RETRAINING")
        try:
            script_path = self.src_dir / "preprocessing" / "retrain_models.py"
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                self.execution_report['steps']['model_retraining'] = 'success'
                return True
            else:
                self.execution_report['steps']['model_retraining'] = 'failed'
                return False
                
        except Exception as e:
            self.execution_report['steps']['model_retraining'] = f'error: {str(e)}'
            return False
    
    def step_validate_predictions(self):
        self.log_section("STEP 5: VALIDATION & TESTING")
        try:
            test_script = f"""
import sys
sys.path.insert(0, r'{self.src_dir / 'models' / 'Xgboost'}')
from predict import RealEstatePricePredictor

predictor = RealEstatePricePredictor()

test_properties = [
    {{'location': 'Anfa, Casablanca', 'surface': 85, 'rooms': 3, 'bedrooms': 2,
      'bathrooms': 1, 'property_category': 'Apartment', 'listing_type': 'For_Sale',
      'garage': True, 'security': True}}
]

for p in test_properties:
    price = predictor.predict_single(p)
    print(price)
"""
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.execution_report['steps']['validation'] = 'success'
                return True
            else:
                self.execution_report['steps']['validation'] = 'failed'
                return False
                
        except Exception as e:
            self.execution_report['steps']['validation'] = 'skipped'
            return False
    
    def generate_report(self):
        self.execution_report['end_time'] = datetime.now().isoformat()
        report_path = self.logs_dir / f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.execution_report, f, indent=2)
    
    def run(self, scrape_mubawab: bool = True, scrape_avito: bool = False, max_pages: int = 5):
        try:
            success = True
            if scrape_mubawab:
                if not self.step_scrape_mubawab(max_pages=max_pages):
                    success = False
                time.sleep(2)
            
            if scrape_avito:
                self.step_scrape_avito()
                time.sleep(2)
            
            if not self.step_consolidate_data():
                success = False
            time.sleep(2)
            
            if not self.step_retrain_models():
                success = False
            time.sleep(2)
            
            self.step_validate_predictions()
            self.generate_report()
            
            return success
            
        except Exception:
            self.generate_report()
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mubawab", action="store_true", default=True)
    parser.add_argument("--avito", action="store_true")
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--no-scrape", action="store_true")
    
    args = parser.parse_args()
    project_root = Path(__file__).parent.parent.resolve()
    orchestrator = PipelineOrchestrator(project_root=str(project_root))
    
    if args.no_scrape:
        success = orchestrator.step_retrain_models()
    else:
        success = orchestrator.run(
            scrape_mubawab=not args.no_scrape,
            scrape_avito=args.avito,
            max_pages=args.pages
        )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
