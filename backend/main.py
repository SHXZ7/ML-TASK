import sys
import os
import types

# Resolve path locations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Add parent directory to path for local execution compatibility
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Fallback for monorepo container deployments (like Railway where Root Directory is /backend)
# If the physical 'backend' directory does not exist relative to SCRIPT_DIR, register a virtual module
if not os.path.exists(os.path.join(PARENT_DIR, "backend")):
    if "backend" not in sys.modules:
        backend_module = types.ModuleType("backend")
        backend_module.__path__ = [SCRIPT_DIR]
        sys.modules["backend"] = backend_module

from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.recommendation.assistant import FashionAssistant

# Initialize FastAPI App
app = FastAPI(
    title="AI Fashion Outfit Recommendation System API",
    description="A FastAPI backend that exposes endpoints for catalog browsing, outfit compatibility matching, and a conversational styling assistant powered by FashionCLIP, Qdrant, and Groq.",
    version="1.0.0"
)

from fastapi.staticfiles import StaticFiles

# Enable CORS (Cross-Origin Resource Sharing)
# Crucial for allowing frontends (e.g. React/Vite/Next.js) to query the API from different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact domains
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files to serve product images locally
images_dir = os.path.join(PARENT_DIR, "images")
app.mount("/images", StaticFiles(directory=images_dir), name="images")

# Initialize the Fashion Assistant (loads RecommendationEngine and connects to Qdrant)
assistant = FashionAssistant()

# --- Pydantic Schemas for Request/Response Validation ---

class ChatRequest(BaseModel):
    message: str

class ProductResponse(BaseModel):
    id: str
    name: str
    brand: str
    price_inr: int
    gender: str
    wear_type: str
    category: str
    category_label: str
    occasion: str
    tags: List[str]
    raw_color: str
    color_family: str
    image_path: str
    rating: Optional[float] = None
    rating_count: Optional[float] = None

class RecommendationResponse(BaseModel):
    source: str
    theme: str
    stylist_rationale: str
    palette: str
    total_price_inr: int
    items: Dict[str, ProductResponse]
    parsed_intent: Optional[Dict] = None

# --- API Endpoints ---

@app.get("/")
def health_check():
    """Health check endpoint to verify backend status."""
    return {
        "status": "healthy",
        "service": "AI Fashion Recommendation API",
        "models": {
            "embeddings": "patrickjohncyh/fashion-clip",
            "llm": "llama-3.3-70b-versatile (Groq)"
        }
    }

@app.get("/api/products", response_model=List[ProductResponse])
def get_products(
    gender: Optional[str] = Query(None, description="Filter products by target gender ('men', 'women')"),
    occasion: Optional[str] = Query(None, description="Filter products by occasion (e.g. 'office', 'casual', 'wedding')"),
    wear_type: Optional[str] = Query(None, description="Filter by wear type ('western', 'ethnic', 'footwear', 'accessory')"),
    category: Optional[str] = Query(None, description="Filter by specific clothing category key (e.g. 'formal-shirts')")
):
    """
    Retrieves all unique products from the fashion catalog.
    Supports filtering by gender, occasion, wear type, and category.
    """
    df = assistant.engine.products_df
    
    # Apply filters dynamically
    if gender:
        df = df[df["gender"].str.lower() == gender.lower()]
    if occasion:
        df = df[df["occasion"].str.lower() == occasion.lower()]
    if wear_type:
        df = df[df["wear_type"].str.lower() == wear_type.lower()]
    if category:
        df = df[df["category"].str.lower() == category.lower()]
        
    products = []
    for _, row in df.iterrows():
        # Get product dictionary with color metadata extracted
        prod = assistant.engine.get_product_by_id(row["id"])
        if prod:
            # Handle NaN values for optional fields (ratings) so Pydantic parses them cleanly
            # Pandas NaN is converted to None
            if isinstance(prod.get("rating"), float) and str(prod.get("rating")) == "nan":
                prod["rating"] = None
            if isinstance(prod.get("rating_count"), float) and str(prod.get("rating_count")) == "nan":
                prod["rating_count"] = None
                
            products.append(ProductResponse(**prod))
            
    return products

@app.get("/api/products/{product_id}", response_model=ProductResponse)
def get_product_details(product_id: str):
    """Retrieves metadata details for a specific product ID."""
    prod = assistant.engine.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found.")
        
    if isinstance(prod.get("rating"), float) and str(prod.get("rating")) == "nan":
        prod["rating"] = None
    if isinstance(prod.get("rating_count"), float) and str(prod.get("rating_count")) == "nan":
        prod["rating_count"] = None
        
    return ProductResponse(**prod)

@app.get("/api/recommend/{product_id}", response_model=RecommendationResponse)
def get_recommendations(product_id: str):
    """
    Directly retrieves compatible outfit coordinates for a selected product.
    Matches curated outfits first (Stage 1), falling back to AI vector compatibility matching (Stage 2).
    """
    recommendation = assistant.engine.get_recommendations_for_product(product_id)
    if "error" in recommendation:
        raise HTTPException(status_code=404, detail=recommendation["error"])
        
    # Clean up NaN ratings in response payload items
    for role, item in recommendation["items"].items():
        if isinstance(item.get("rating"), float) and str(item.get("rating")) == "nan":
            item["rating"] = None
        if isinstance(item.get("rating_count"), float) and str(item.get("rating_count")) == "nan":
            item["rating_count"] = None
            
    return RecommendationResponse(**recommendation)

@app.post("/api/chat", response_model=RecommendationResponse)
def chat_styling_assistant(request: ChatRequest):
    """
    Conversational Fashion Assistant.
    Parses user requests, performs multi-modal search, builds outfits, and generates stylized explanations.
    """
    recommendation = assistant.recommend_from_chat(request.message)
    if "error" in recommendation:
        raise HTTPException(status_code=422, detail=recommendation["error"])
        
    # Clean up NaN ratings in response payload items
    for role, item in recommendation["items"].items():
        if isinstance(item.get("rating"), float) and str(item.get("rating")) == "nan":
            item["rating"] = None
        if isinstance(item.get("rating_count"), float) and str(item.get("rating_count")) == "nan":
            item["rating_count"] = None
            
    return RecommendationResponse(**recommendation)

if __name__ == "__main__":
    import uvicorn
    # Launch uvicorn server on localhost:8000 (Trigger reload for CSV update)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
