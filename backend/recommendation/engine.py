import os
import re
import uuid
import pandas as pd
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Load environment variables
load_dotenv()

# Resolve path locations dynamically relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
PRODUCTS_CSV = os.path.join(WORKSPACE_ROOT, "products.csv")
OUTFITS_CSV = os.path.join(WORKSPACE_ROOT, "outfits.csv")

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "products"

# Initialize Qdrant Client
def get_qdrant_client():
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Styling Category Roles
FULL_BODY_CATEGORIES = {
    "suits", "sherwanis", "party-dresses", "wedding-sarees", 
    "sharara-sets", "casual-dresses", "maxi-dresses", 
    "co-ord-sets", "salwar-suits", "kurta-sets"
}

TOPWEAR_CATEGORIES = {
    "formal-shirts", "linen-shirts", "casual-shirts", "party-shirts", 
    "tshirts", "polo-tshirts", "sweatshirts", "activewear", 
    "tops", "sweaters"
}

BOTTOMWEAR_CATEGORIES = {
    "trousers", "jeans", "chinos", "shorts", "skirts", 
    "leggings", "track-pants"
}

LAYER_CATEGORIES = {
    "blazers", "long-coats", "denim-jackets", "nehru-jackets"
}

FOOTWEAR_CATEGORIES = {
    "heels", "ethnic-footwear", "formal-shoes", "boots", 
    "running-shoes", "sneakers", "flats", "loafers", "sandals"
}

ACCESSORY_CATEGORIES = {
    "clutches", "necklaces", "handbags", "watches", 
    "earrings", "sunglasses", "caps"
}

class RecommendationEngine:
    def __init__(self):
        self.products_df = pd.read_csv(PRODUCTS_CSV)
        self.outfits_df = pd.read_csv(OUTFITS_CSV)
        self.qdrant_client = get_qdrant_client()

    def get_product_by_id(self, product_id: str) -> dict:
        """Helper to get product metadata from local CSV by product ID."""
        row = self.products_df[self.products_df['id'] == product_id]
        if row.empty:
            return None
        # Extract color using ingest logic dynamically if not in CSV (CSV doesn't store raw_color, but Qdrant payload does)
        # However, to be consistent and avoid calling Qdrant unnecessarily, we extract it from name/description
        from backend.scripts.ingest import extract_color_info
        raw_color, color_family = extract_color_info(f"{row.iloc[0]['name']} {row.iloc[0]['description']}")
        
        prod_dict = row.iloc[0].to_dict()
        prod_dict['raw_color'] = raw_color
        prod_dict['color_family'] = color_family
        
        # Map 'image' column to 'image_path'
        prod_dict['image_path'] = prod_dict.get('image')
        
        # Parse tags semicolon-separated string into a list of strings
        tags_val = prod_dict.get('tags')
        if isinstance(tags_val, str):
            prod_dict['tags'] = [t.strip() for t in tags_val.split(";") if t.strip()]
        else:
            prod_dict['tags'] = []
            
        # Standardize NaN rating values to None
        for key in ['rating', 'rating_count']:
            val = prod_dict.get(key)
            if pd.isna(val):
                prod_dict[key] = None
                
        return prod_dict

    def find_curated_outfit(self, product_id: str) -> dict:
        """
        Stage 1: Look up if the product belongs to any curated outfits in outfits.csv.
        Returns a dictionary representing the curated outfit details if found.
        """
        # Search all columns that contain product IDs
        id_cols = ['hero_id', 'second_id', 'layer_id', 'footwear_id', 'accessory_1_id', 'accessory_2_id']
        for _, outfit in self.outfits_df.iterrows():
            for col in id_cols:
                if pd.notna(outfit[col]) and outfit[col] == product_id:
                    # Found curated outfit! Resolve all items
                    items = {}
                    for item_role in ['hero', 'second', 'layer', 'footwear', 'accessory_1', 'accessory_2']:
                        id_key = f"{item_role}_id"
                        if pd.notna(outfit[id_key]):
                            prod = self.get_product_by_id(outfit[id_key])
                            if prod:
                                items[item_role] = prod
                                
                    return {
                        "source": "curated",
                        "outfit_id": outfit["outfit_id"],
                        "theme": outfit["theme"],
                        "stylist_rationale": outfit["stylist_rationale"],
                        "palette": outfit["palette"],
                        "total_price_inr": int(outfit["total_price_inr"]),
                        "items": items
                    }
        return None

    def get_recommendations_for_product(self, product_id: str) -> dict:
        """
        Main recommendation entrypoint. Given a product ID:
        1. Checks curated outfits (Stage 1).
        2. Falls back to filtered vector search (Stage 2).
        """
        product = self.get_product_by_id(product_id)
        if not product:
            return {"error": "Product not found"}

        # --- Stage 1: Curated Outfit Lookup ---
        curated_outfit = self.find_curated_outfit(product_id)
        if curated_outfit:
            # Reformat to match response structure (excluding the input product from recommendations list)
            return curated_outfit

        # --- Stage 2: Fallback (AI-Composed Vector Search) ---
        return self._generate_ai_outfit(product)

    def _generate_ai_outfit(self, anchor_product: dict) -> dict:
        """
        Stage 2 Logic: Generates a compatible outfit from scratch based on vector similarity
        constrained by gender, category slot rules, and color palettes.
        """
        gender = anchor_product["gender"]
        occasion = anchor_product["occasion"]
        category = anchor_product["category"]
        
        # 1. Determine what styling roles we need to fetch
        slots_needed = []
        
        if category in FULL_BODY_CATEGORIES:
            slots_needed = [("footwear", FOOTWEAR_CATEGORIES), ("accessory_1", ACCESSORY_CATEGORIES)]
        elif category in TOPWEAR_CATEGORIES:
            slots_needed = [("second", BOTTOMWEAR_CATEGORIES), ("footwear", FOOTWEAR_CATEGORIES), ("accessory_1", ACCESSORY_CATEGORIES)]
        elif category in BOTTOMWEAR_CATEGORIES:
            slots_needed = [("hero", TOPWEAR_CATEGORIES), ("footwear", FOOTWEAR_CATEGORIES), ("accessory_1", ACCESSORY_CATEGORIES)]
        elif category in FOOTWEAR_CATEGORIES:
            # If starting from shoe, search for a Topwear Hero first, then build outfit
            slots_needed = [("hero", TOPWEAR_CATEGORIES), ("second", BOTTOMWEAR_CATEGORIES), ("accessory_1", ACCESSORY_CATEGORIES)]
        elif category in LAYER_CATEGORIES:
            # If starting from outerwear, find a Topwear Hero first, then build outfit
            slots_needed = [("hero", TOPWEAR_CATEGORIES), ("second", BOTTOMWEAR_CATEGORIES), ("footwear", FOOTWEAR_CATEGORIES)]
        else: # Accessory
            slots_needed = [("hero", TOPWEAR_CATEGORIES), ("second", BOTTOMWEAR_CATEGORIES), ("footwear", FOOTWEAR_CATEGORIES)]

        # Fetch anchor vector from Qdrant Cloud to perform visual similarity search
        anchor_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, anchor_product["id"]))
        try:
            res = self.qdrant_client.retrieve(collection_name=COLLECTION_NAME, ids=[anchor_uuid], with_vectors=True)
            if not res or len(res) == 0:
                # Fallback: if vector is not found, use a zero-vector (will retrieve based on filters only)
                anchor_vector = [0.0] * 512
            else:
                anchor_vector = res[0].vector
        except Exception as e:
            print(f"⚠️ Warning retrieving vector for {anchor_product['id']}: {e}")
            anchor_vector = [0.0] * 512

        # 2. Query Qdrant for each required slot
        items = {"hero": anchor_product}
        
        # If the input itself is a secondary item, re-assign it to its proper slot
        if category in BOTTOMWEAR_CATEGORIES:
            items = {"second": anchor_product}
        elif category in FOOTWEAR_CATEGORIES:
            items = {"footwear": anchor_product}
        elif category in LAYER_CATEGORIES:
            items = {"layer": anchor_product}
        elif category in ACCESSORY_CATEGORIES:
            items = {"accessory_1": anchor_product}

        for slot_name, allowed_categories in slots_needed:
            # Apply color rule constraints
            excluded_colors = []
            anchor_color = anchor_product.get("color_family", "unknown")
            
            # Monochromatic exception rule: Block identical colors except for Black and Blue/Denim
            if anchor_color not in ["black", "blue", "unknown"]:
                excluded_colors.append(anchor_color)
                
            # Perform query on Qdrant
            matching_item = self._query_qdrant_slot(
                vector=anchor_vector,
                gender=gender,
                occasion=occasion,
                allowed_categories=allowed_categories,
                excluded_colors=excluded_colors
            )
            
            if matching_item:
                items[slot_name] = matching_item

        # Compute price sum
        total_price = sum(item["price_inr"] for item in items.values() if item)
        
        # Compile color list
        palette_list = [item["color_family"] for item in items.values() if item and item.get("color_family") != "unknown"]
        
        return {
            "source": "ai",
            "theme": f"AI {occasion.capitalize()} Styling",
            "stylist_rationale": self._generate_ai_rationale(items, occasion),
            "palette": " / ".join(set(palette_list)),
            "total_price_inr": total_price,
            "items": items
        }

    def _query_qdrant_slot(self, vector, gender, occasion, allowed_categories, excluded_colors) -> dict:
        """
        Executes a vector search in Qdrant applying hard filters (gender, category list) 
        and color clash exclusions, returning the best matching product.
        """
        conditions = [
            FieldCondition(key="gender", match=MatchValue(value=gender)),
        ]
        
        # Build category filter
        # Qdrant match supports single values or list of values
        category_conditions = [FieldCondition(key="category", match=MatchValue(value=cat)) for cat in allowed_categories]
        
        # Build color exclusion filters if any
        color_conditions = []
        for color in excluded_colors:
            # We filter out the matching color using a must_not condition in our filter
            color_conditions.append(FieldCondition(key="color_family", match=MatchValue(value=color)))
            
        # Combine filters
        # Category list needs to be a "should" match (item belongs to any of these categories)
        # Gender must be a "must" match
        # Excluded colors must be a "must_not" match
        qdrant_filter = Filter(
            must=conditions,
            should=category_conditions,
            must_not=color_conditions if color_conditions else None
        )
        
        try:
            # Run query
            # We first try to match the exact occasion. If no results, we search broadly ignoring occasion
            # This handles sparse catalog coverage for vacation, winter, etc.
            occasion_filter = Filter(
                must=conditions + [FieldCondition(key="occasion", match=MatchValue(value=occasion))],
                should=category_conditions,
                must_not=color_conditions if color_conditions else None
            )
            
            search_results = self.qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                query_filter=occasion_filter,
                limit=1
            )
            
            if not search_results or not search_results.points:
                # Occasion match failed (empty result). Fallback to general search without occasion filter
                search_results = self.qdrant_client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=vector,
                    query_filter=qdrant_filter,
                    limit=1
                )
                
            if search_results and search_results.points:
                return search_results.points[0].payload
        except Exception as e:
            import traceback
            print(f"❌ Error during Qdrant search: {e}")
            traceback.print_exc()
            
        return None

    def _generate_ai_rationale(self, items: dict, occasion: str) -> str:
        """Generates a rule-based styling explanation for the recommendation."""
        hero = items.get("hero")
        second = items.get("second")
        footwear = items.get("footwear")
        
        hero_desc = hero["name"] if hero else "this primary piece"
        hero_color = hero.get("color_family", "neutral") if hero else "neutral"
        
        rationale = f"This outfit is dynamically selected for a {occasion} occasion. "
        
        if hero and second:
            rationale += f"We paired the {hero_color} {hero['category_label']} with the {second.get('color_family', 'neutral')} {second['category_label']} to create a balanced, color-compatible contrast. "
        elif hero:
            rationale += f"The {hero_color} {hero['category_label']} anchors the look. "
            
        if footwear:
            rationale += f"It is completed with {footwear['name']} to coordinate the style lines."
            
        return rationale
