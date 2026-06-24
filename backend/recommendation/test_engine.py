import sys
import os

# Adjust sys.path to run the script from the root workspace folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.recommendation.engine import RecommendationEngine

def print_outfit(outfit):
    print(f"\n==========================================")
    print(f"OUTFLOW SOURCE : {outfit.get('source', 'unknown').upper()}")
    print(f"THEME          : {outfit.get('theme')}")
    print(f"PRICE          : {outfit.get('total_price_inr')} INR")
    print(f"PALETTE        : {outfit.get('palette')}")
    print(f"RATIONALE      : {outfit.get('stylist_rationale')}")
    print(f"------------------------------------------")
    for role, item in outfit.get("items", {}).items():
        print(f"-> {role.upper():12}: {item['name']} ({item['brand']})")
        print(f"   ID          : {item['id']}")
        print(f"   Category    : {item['category']}")
        print(f"   Color       : {item.get('raw_color')} ({item.get('color_family')})")
        print(f"   Price       : {item['price_inr']} INR")
        print(f"   Occasion    : {item['occasion']}")
    print(f"==========================================\n")

def main():
    print("🧪 Running Recommendation Engine Verification Tests...")
    
    try:
        engine = RecommendationEngine()
        print("✅ Recommendation Engine initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize engine: {e}")
        return

    # --- Test Case 1: Curated Outfit Lookup (Stage 1) ---
    print("\n------------------------------------------------")
    print("Test Case 1: Testing Curated Outfit Lookup (Stage 1)")
    # 'ajio_703182002' is the Women Bodycon Midi Length Dress from curated Outfit W1
    test_id_curated = "ajio_703182002" 
    print(f"Querying product: {test_id_curated}...")
    
    outfit_curated = engine.get_recommendations_for_product(test_id_curated)
    if "error" in outfit_curated:
        print(f"❌ Test Case 1 Failed: {outfit_curated['error']}")
    else:
        print("✅ Test Case 1 Passed! Curated outfit retrieved:")
        print_outfit(outfit_curated)

    # --- Test Case 2: AI Fallback Outfit Generation (Stage 2) ---
    print("\n------------------------------------------------")
    print("Test Case 2: Testing AI Fallback Outfit (Stage 2)")
    # To test Stage 2 fallback, we force the AI generation on a product
    # Let's use the 'myntra_28569210' (Cotton Slim Fit Formal Shirt - White)
    test_product_id = "myntra_28569210"
    product = engine.get_product_by_id(test_product_id)
    
    if not product:
        print(f"❌ Test Case 2 Failed: Product {test_product_id} not found in catalog.")
        return
        
    print(f"Generating AI fallback outfit for product: {product['name']} (Color: {product['color_family']})...")
    outfit_ai = engine._generate_ai_outfit(product)
    
    if "error" in outfit_ai:
        print(f"❌ Test Case 2 Failed: {outfit_ai['error']}")
    else:
        print("✅ Test Case 2 Passed! AI Outfit generated successfully:")
        print_outfit(outfit_ai)
        
        # Verify color rules are respected
        hero_color = product.get("color_family")
        for role, item in outfit_ai.get("items", {}).items():
            if role == "second":
                second_color = item.get("color_family")
                print(f"Verifying Color Rule: Hero Color ({hero_color}) vs. Bottomwear Color ({second_color})")
                if hero_color == second_color and hero_color not in ["black", "blue"]:
                    print(f"❌ Color clash detected! Matched identical color: {hero_color}")
                else:
                    print(f"✅ Color rule verified: Allowed combination.")

if __name__ == "__main__":
    main()
