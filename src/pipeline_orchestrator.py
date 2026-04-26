"""
MASTER SCRAPING & RETRAINING ORCHESTRATOR
Complete pipeline: Scrape → Clean → Retrain → Validate
Handles both Mubawab and Avito data sources
"""

import subprocess
import sys
import logging
from pathlib import Path
from datetime import datetime
import time
import json

# Setup logging
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
    """Orchestrates complete scraping and retraining pipeline"""
    
    def __init__(self, project_root: str = ".."):
        self.project_root = Path(project_root).resolve()
        self.data_dir = self.project_root / "data"
        self.src_dir = self.project_root / "src"
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Data dir: {self.data_dir}")
        logger.info(f"Src dir: {self.src_dir}")
        
        self.execution_report = {
            'start_time': datetime.now().isoformat(),
            'steps': {},
            'total_properties_scraped': 0,
            'model_metrics': {}
        }
    
    def log_section(self, title: str):
        """Print formatted section header"""
        logger.info("\n" + "="*70)
        logger.info(f"  {title}")
        logger.info("="*70)
    
    def step_scrape_mubawab(self, max_pages: int = 5, timeout: int = 3600):
        """Execute Mubawab scraper"""
        self.log_section("STEP 1: SCRAPING MUBAWAB")
        
        try:
            logger.info(f"Scraping Mubawab (max {max_pages} pages per listing type)...")
            logger.info("This may take several minutes depending on number of pages...")
            
            script_path = self.src_dir / "scrap" / "mubawab_scraper_modern.py"
            
            # Update script with max pages
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
                logger.info("[OK] Mubawab scraping completed successfully")
                self.execution_report['steps']['mubawab_scraping'] = 'success'
                # Try to extract property count from output
                if 'properties_scraped' in result.stdout or 'Total Properties' in result.stdout:
                    logger.info(result.stdout[-500:])  # Last 500 chars
                return True
            else:
                logger.error(f"Mubawab scraping failed: {result.stderr}")
                self.execution_report['steps']['mubawab_scraping'] = 'failed'
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Mubawab scraping timed out after {timeout} seconds")
            self.execution_report['steps']['mubawab_scraping'] = 'timeout'
            return False
        except Exception as e:
            logger.error(f"Error running Mubawab scraper: {e}")
            self.execution_report['steps']['mubawab_scraping'] = f'error: {str(e)}'
            return False
    
    def step_scrape_avito(self, timeout: int = 1800):
        """Execute Avito Scrapy spider"""
        self.log_section("STEP 2: SCRAPING AVITO (OPTIONAL)")
        
        try:
            logger.info("Scraping Avito using Scrapy...")
            logger.info("Note: This requires Scrapy configuration in scrapping/ directory")
            
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
                logger.info("[OK] Avito scraping completed")
                self.execution_report['steps']['avito_scraping'] = 'success'
                return True
            else:
                logger.warning(f"Avito scraping warning: {result.stderr[:500]}")
                logger.info("Continuing with Mubawab data only...")
                self.execution_report['steps']['avito_scraping'] = 'skipped'
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Avito scraping timed out after {timeout} seconds")
            logger.info("Continuing with Mubawab data only...")
            self.execution_report['steps']['avito_scraping'] = 'timeout'
            return False
        except Exception as e:
            logger.warning(f"Avito scraping not available: {e}")
            logger.info("Continuing with Mubawab data only...")
            self.execution_report['steps']['avito_scraping'] = f'skipped: {str(e)}'
            return False
    
    def step_consolidate_data(self):
        """Consolidate and clean data"""
        self.log_section("STEP 3: DATA CONSOLIDATION & CLEANING")
        
        try:
            # Run retrain script which includes consolidation
            script_path = self.src_dir / "preprocessing" / "retrain_models.py"
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                logger.info("[OK] Data consolidation completed")
                self.execution_report['steps']['data_consolidation'] = 'success'
                
                # Parse output for metrics
                if 'After cleaning:' in result.stdout:
                    logger.info(result.stdout[result.stdout.find('After cleaning:'):])
                
                return True
            else:
                logger.error(f"Data consolidation failed: {result.stderr}")
                self.execution_report['steps']['data_consolidation'] = 'failed'
                return False
                
        except Exception as e:
            logger.error(f"Error in data consolidation: {e}")
            self.execution_report['steps']['data_consolidation'] = f'error: {str(e)}'
            return False
    
    def step_retrain_models(self):
        """Retrain models with consolidated data (delegates to retrain_models.py)"""
        self.log_section("STEP 4: MODEL RETRAINING")
        # Note: step_consolidate_data already runs retrain_models.py which
        # does both data consolidation AND model retraining in one pass.
        # This step is kept for explicit re-runs when consolidation is skipped.
        
        try:
            logger.info("Retraining XGBoost model with current prices...")
            
            script_path = self.src_dir / "preprocessing" / "retrain_models.py"
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                logger.info("[OK] Model retraining completed")
                self.execution_report['steps']['model_retraining'] = 'success'
                return True
            else:
                logger.error(f"Model retraining failed: {result.stderr}")
                self.execution_report['steps']['model_retraining'] = 'failed'
                return False
                
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
            self.execution_report['steps']['model_retraining'] = f'error: {str(e)}'
            return False
    
    def step_validate_predictions(self):
        """Validate with test predictions"""
        self.log_section("STEP 5: VALIDATION & TESTING")
        
        try:
            logger.info("Testing predictions with sample properties...")
            
            test_script = f"""
import sys
sys.path.insert(0, r'{self.src_dir / 'models' / 'Xgboost'}')
from predict import RealEstatePricePredictor

predictor = RealEstatePricePredictor()

test_properties = [
    {{'location': 'Anfa, Casablanca', 'surface': 85, 'rooms': 3, 'bedrooms': 2,
      'bathrooms': 1, 'property_category': 'Apartment', 'listing_type': 'For_Sale',
      'garage': True, 'security': True}},
    {{'location': 'Gueliz, Marrakech', 'surface': 120, 'rooms': 4, 'bedrooms': 3,
      'bathrooms': 2, 'property_category': 'Apartment', 'listing_type': 'For_Sale',
      'terrace': True}},
    {{'location': 'Hassan, Rabat', 'surface': 95, 'rooms': 3, 'bedrooms': 2,
      'bathrooms': 1, 'property_category': 'Apartment', 'listing_type': 'For_Sale',
      'elevator': True}},
]

for p in test_properties:
    price = predictor.predict_single(p)
    print(f"  {{p['location']}} | {{p['surface']}}m2 | {{p['property_category']}}")
    print(f"  => {{price:,.0f}} MAD  ({{price/p['surface']:,.0f}} MAD/m2)")
    print()
"""
            
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("[OK] Validation tests passed")
                logger.info("\nTest Results:")
                logger.info(result.stdout)
                self.execution_report['steps']['validation'] = 'success'
                return True
            else:
                logger.warning(f"Validation tests had issues: {result.stderr}")
                self.execution_report['steps']['validation'] = 'completed_with_warnings'
                return False
                
        except Exception as e:
            logger.warning(f"Validation testing skipped: {e}")
            self.execution_report['steps']['validation'] = 'skipped'
            return False
    
    def generate_report(self):
        """Generate final execution report"""
        self.log_section("EXECUTION REPORT")
        
        self.execution_report['end_time'] = datetime.now().isoformat()
        
        logger.info(f"""
=====================================================
           PIPELINE EXECUTION COMPLETED
=====================================================
 Start Time: {self.execution_report['start_time']:<38}
 End Time:   {self.execution_report['end_time']:<38}
=====================================================
 STEPS COMPLETED:
        """)
        
        for step, status in self.execution_report['steps'].items():
            status_symbol = "[+]" if status == "success" else "[!]" if status == "skipped" else "[-]"
            logger.info(f" {status_symbol} {step:<50} {str(status):<6}")
        
        logger.info(f"""
=====================================================
 NEXT STEPS:
 1. Run: python src/models/Xgboost/prediction_app.py
 2. Enter property details for prediction
 3. Verify prices match current market values
 4. Monitor logs/pipeline_execution.log for details
=====================================================
        """)
        
        # Save report
        report_path = self.logs_dir / f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.execution_report, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_path}")
    
    def run(self, scrape_mubawab: bool = True, scrape_avito: bool = False, max_pages: int = 5):
        """Execute complete pipeline"""
        try:
            logger.info(f"""
=====================================================
  REAL ESTATE DATA PIPELINE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Current Market Price Data Collection & Model Retraining
=====================================================
            """)
            
            success = True
            
            # Step 1: Scrape Mubawab
            if scrape_mubawab:
                if not self.step_scrape_mubawab(max_pages=max_pages):
                    logger.warning("Mubawab scraping had issues, continuing...")
                time.sleep(2)
            
            # Step 2: Scrape Avito (optional)
            if scrape_avito:
                self.step_scrape_avito()
                time.sleep(2)
            
            # Step 3: Consolidate data
            if not self.step_consolidate_data():
                success = False
            time.sleep(2)
            
            # Step 4: Retrain models
            if not self.step_retrain_models():
                logger.warning("Model retraining had issues")
            time.sleep(2)
            
            # Step 5: Validate
            self.step_validate_predictions()
            
            # Generate report
            self.generate_report()
            
            return success
            
        except KeyboardInterrupt:
            logger.warning("\nPipeline interrupted by user")
            self.generate_report()
            return False
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.generate_report()
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real Estate Data Pipeline Orchestrator")
    parser.add_argument("--mubawab", action="store_true", default=True, help="Scrape Mubawab (default: True)")
    parser.add_argument("--avito", action="store_true", help="Scrape Avito (optional)")
    parser.add_argument("--pages", type=int, default=5, help="Max pages to scrape per listing type (default: 5)")
    parser.add_argument("--no-scrape", action="store_true", help="Skip scraping, only retrain models")
    
    args = parser.parse_args()
    
    # Get absolute path to project root (one level up from src)
    project_root = Path(__file__).parent.parent.resolve()
    orchestrator = PipelineOrchestrator(project_root=str(project_root))
    
    if args.no_scrape:
        logger.info("Skipping scraping, retraining models only...")
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
