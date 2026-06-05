# test_finder.py
from src.core.database import init_db
from src.modules.lead_finder.finder import LeadFinder

init_db()

finder = LeadFinder()
try:
    leads = finder.find(
        category="restaurantes",
        city="Rosario",
        max_results=10
    )
    print(f"\nTotal guardados: {len(leads)}")
finally:
    finder.close()