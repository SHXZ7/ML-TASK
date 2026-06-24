import os
import re
import json
import torch
from groq import Groq
from transformers import CLIPProcessor, CLIPModel
from qdrant_client.models import Filter, FieldCondition, MatchValue

from backend.recommendation.engine import (
    RecommendationEngine, 
    COLLECTION_NAME, 
    FULL_BODY_CATEGORIES, 
    TOPWEAR_CATEGORIES,
    BOTTOMWEAR_CATEGORIES,
    LAYER_CATEGORIES,
    FOOTWEAR_CATEGORIES,
    ACCESSORY_CATEGORIES
)

# Load Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Allowed occasion categories in the database
ALLOWED_OCCASIONS = {'casual', 'party', 'office', 'festive', 'wedding', 'sports', 'vacation', 'winter'}

# Shared FashionCLIP model references (loaded lazily to save memory)
_model = None
_processor = None
_device = None

def get_fashionclip_model():
    """Lazy loader for FashionCLIP to avoid reloading it across files."""
    global _model, _processor, _device
    if _model is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = CLIPModel.from_pretrained("patrickjohncyh/fashion-clip").to(_device)
        _processor = CLIPProcessor.from_pretrained("patrickjohncyh/fashion-clip")
    return _model, _processor, _device

class FashionAssistant:
    def __init__(self):
        self.engine = RecommendationEngine()
        # Initialize Groq Model
        if GROQ_API_KEY:
            self.llm = Groq(api_key=GROQ_API_KEY)
            self.llm_model = "llama-3.3-70b-versatile"
        else:
            self.llm = None
            print("⚠️ Warning: GROQ_API_KEY not found in environment. Chat functionality will fall back to rule-based parser.")

    def parse_user_query(self, query: str) -> dict:
        """
        Step 1: Uses Groq LLM to parse natural language requests into structured parameters.
        Includes defensive fallback parsing in case LLM is offline or fails validation.
        """
        default_intent = {"gender": None, "occasion": None, "search_keywords": query, "is_fashion_related": True}
        
        if not self.llm:
            return self._fallback_rule_based_parse(query)

        prompt = f"""
You are an AI Fashion Assistant parser. Your job is to parse a user's natural language query and extract styling parameters, while filtering out gibberish, greetings, or completely off-topic queries.

Allowed Occasions (You MUST return exactly one of these or null):
- casual
- office
- party
- festive
- wedding
- sports
- vacation
- winter

You must return a JSON object with the exact fields:
1. "gender": "men", "women", or null (if not specified or unisex)
2. "occasion": one of the Allowed Occasions listed above, or null (if not matching)
3. "search_keywords": a descriptive text query (e.g. "navy linen shirt", "cotton dress", "running shoes") summarizing the main clothing item, or null if the query is unrelated.
4. "is_fashion_related": true or false. Set to false if the query is gibberish (like "cdv", "xyz", "aksjdhf"), a greeting (like "hello", "hi"), or completely unrelated to fashion/clothing advice (like "how is the weather").

Do not include any markdown styling or text outside the JSON. Return only the raw JSON.

User Query: "{query}"
"""
        try:
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"} # Force JSON format
            )
            clean_text = response.choices[0].message.content.strip()
            intent = json.loads(clean_text)
            
            # Post-parsing defensive validation
            if intent.get("occasion") not in ALLOWED_OCCASIONS:
                intent["occasion"] = None
                
            if intent.get("gender") not in ["men", "women"]:
                intent["gender"] = None
                
            if "is_fashion_related" not in intent:
                intent["is_fashion_related"] = True
                
            return intent
        except Exception as e:
            print(f"⚠️ Groq Intent Parser failed: {e}. Falling back to rule-based parser.")
            return self._fallback_rule_based_parse(query)

    def _fallback_rule_based_parse(self, query: str) -> dict:
        """Simple keyword-based parser in case LLM is unavailable."""
        query_lower = query.lower()
        gender = None
        if "men" in query_lower or "man" in query_lower or "boy" in query_lower or "guy" in query_lower:
            gender = "men"
        elif "women" in query_lower or "woman" in query_lower or "girl" in query_lower or "lady" in query_lower:
            gender = "women"
            
        occasion = None
        for occ in ALLOWED_OCCASIONS:
            if occ in query_lower:
                occasion = occ
                break
                
        # Basic check to filter out empty/extremely short gibberish in fallback mode
        is_related = True
        if len(query.strip()) < 3 and not (gender or occasion):
            is_related = False
            
        return {
            "gender": gender,
            "occasion": occasion,
            "search_keywords": query,
            "is_fashion_related": is_related
        }

    def embed_text_query(self, search_keywords: str) -> list:
        """Step 2: Converts the search keywords into a 512-dimension text vector using FashionCLIP."""
        model, processor, device = get_fashionclip_model()
        inputs = processor(text=[search_keywords], return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            text_features = model.get_text_features(**inputs)
            # Normalize embedding
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            return text_features[0].cpu().numpy().tolist()

    def find_initial_hero(self, keywords: str, gender: str = None, occasion: str = None) -> dict:
        """
        Step 3: Queries Qdrant using the text embedding vector and category/gender/occasion filters
        to retrieve the starting product (Hero).
        """
        # Local mock shortcut to allow testing Stage 2 AI Fallback in conversational chat
        if keywords and ("zara" in keywords.lower() or "test" in keywords.lower()):
            prod = self.engine.get_product_by_id("ajio_test_999")
            if prod:
                return prod
                
        # Embed the query
        text_vector = self.embed_text_query(keywords)
        
        # Build Qdrant Filters
        conditions = []
        if gender:
            conditions.append(FieldCondition(key="gender", match=MatchValue(value=gender)))
            
        # We search both Full-body and Topwear categories as potential starting points (Hero items)
        allowed_hero_categories = list(FULL_BODY_CATEGORIES) + list(TOPWEAR_CATEGORIES)
        category_conditions = [FieldCondition(key="category", match=MatchValue(value=cat)) for cat in allowed_hero_categories]
        
        # Combine filters
        qdrant_filter = Filter(
            must=conditions,
            should=category_conditions
        )
        
        try:
            # Attempt occasion-aware search first
            if occasion:
                occasion_filter = Filter(
                    must=conditions + [FieldCondition(key="occasion", match=MatchValue(value=occasion))],
                    should=category_conditions
                )
                res = self.engine.qdrant_client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=text_vector,
                    query_filter=occasion_filter,
                    limit=1
                )
                if res and res.points:
                    return res.points[0].payload
                    
            # Fallback to general search if occasion search yielded nothing or occasion is None
            res = self.engine.qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=text_vector,
                query_filter=qdrant_filter,
                limit=1
            )
            if res and res.points:
                return res.points[0].payload
        except Exception as e:
            print(f"❌ Error during initial hero search: {e}")
            
        return None

    def generate_stylist_rationale(self, user_query: str, occasion: str, items: dict) -> str:
        """Step 4: Generates a warm, friendly, context-aware explanation using Groq."""
        if not self.llm:
            return "This outfit coordinates well and fits the style requirements for your occasion."
            
        # Format the items for the prompt
        items_desc = []
        for role, item in items.items():
            items_desc.append(f"- {role.capitalize()}: {item['name']} (Brand: {item['brand']}, Color: {item.get('color_family')})")
        items_str = "\n".join(items_desc)
        
        prompt = f"""
You are a warm, professional AI Fashion Stylist. You have selected the following outfit for a client:

Client's Original Request: "{user_query}"
Occasion: {occasion if occasion else "general wear"}

Outfit Recommendation:
{items_str}

Write a friendly, personalized 2-3 sentence explanation explaining why this combination is compatible and matches their context. 
If there is a mismatch between what the client requested (e.g., specific colors, brands, or clothing items) and the actual items in the recommended outfit (because the exact request is not in our catalog), make sure to acknowledge this deviation gracefully (e.g., "We don't have a yellow dress in our catalog, so I styled this classic black dress from our lookbook...").
Focus on styling coordination (colors, materials) and occasion appropriateness. Do not mention product IDs or technical details. Keep it conversational.
Stylist Rationale:
"""
        try:
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Groq Rationale Generation failed: {e}")
            return "This outfit is designed to provide clean lines and a coordinating color palette suitable for your occasion."

    def recommend_from_chat(self, message: str) -> dict:
        """
        Full End-to-End Chat Assistant pipeline:
        1. Parse intent.
        2. Retrieve matching Hero product via semantic text search.
        3. Retrieve compatible items (Stage 1 or Stage 2 Fallback).
        4. Generate personalized stylist explanation.
        """
        # 1. Parse natural language request
        intent = self.parse_user_query(message)
        gender = intent["gender"]
        occasion = intent["occasion"]
        keywords = intent["search_keywords"]
        
        # Check fashion relevance
        if not intent.get("is_fashion_related", True):
            return {
                "error": "I couldn't quite find any fashion context in your message. Could you try describing an outfit, occasion, or style you'd like me to coordinate? (e.g., 'casual outfit for a summer date' or 'smart casual for an office meeting').",
                "parsed_intent": intent
            }
            
        if not keywords or not keywords.strip():
            return {
                "error": "It looks like your request didn't specify a clothing type or keywords. Please let me know what items or look you are searching for!",
                "parsed_intent": intent
            }
            
        # 2. Retrieve initial anchor product (Hero)
        hero_item = self.find_initial_hero(
            keywords=keywords,
            gender=gender,
            occasion=occasion
        )
        
        if not hero_item:
            return {
                "error": f"Could not find any suitable starting products in our catalog for '{keywords}'. Try searching for different items or styles.",
                "parsed_intent": intent
            }
            
        # 3. Retrieve compatible outfit coordinates
        outfit = self.engine.get_recommendations_for_product(hero_item["id"])
        
        # 4. Generate personalized explanation
        stylist_rationale = self.generate_stylist_rationale(
            user_query=message,
            occasion=occasion,
            items=outfit["items"]
        )
        
        outfit["stylist_rationale"] = stylist_rationale
        outfit["parsed_intent"] = intent
        return outfit
