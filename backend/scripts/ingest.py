import os
import re
import uuid
import pandas as pd
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Resolve path locations dynamically relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
PRODUCTS_CSV = os.path.join(WORKSPACE_ROOT, "products.csv")

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "products"

# Color Normalization Map (Refined for Fashion / Styling)
COLOR_FAMILY_MAP = {
    # Blue family
    "navy blue": "blue",
    "sky blue": "blue",
    "royal blue": "blue",
    "navy": "blue",
    "blue": "blue",
    "indigo": "blue",
    
    # Teal family (distinct from blue/green for fashion purposes)
    "teal": "teal",
    
    # Grey family
    "charcoal": "grey",
    "grey": "grey",
    "gray": "grey",
    
    # White family
    "off-white": "white",
    "white": "white",
    "ivory": "white",
    
    # Red/Pink family
    "red": "red",
    "maroon": "red",
    "burgundy": "red",
    "magenta": "red",
    "rust": "red",
    "pink": "pink",
    "rose": "pink",
    "peach": "pink",
    
    # Green family
    "green": "green",
    "olive": "green",
    "sage": "green",
    "sea green": "green",
    "emerald": "green",
    
    # Brown family
    "brown": "brown",
    
    # Beige/Khaki/Tan family (light neutrals, styled differently than dark brown)
    "beige": "beige",
    "khaki": "beige",
    "tan": "beige",
    "cream": "beige",
    
    # Black family
    "black": "black",
    
    # Purple family
    "purple": "purple",
    "lavender": "purple",
    "plum": "purple",
    
    # Orange family
    "orange": "orange",
    "coral": "orange",
    "burnt orange": "orange",
    
    # Metal families (critical for accessories and watch styling)
    "gold": "gold",
    "silver": "silver"
}

def extract_color_info(text):
    """
    Two-stage rule-based color family extraction.
    Stage 1: Scan titles and descriptions for key color phrases using word boundaries.
    Stage 2: Normalize matched color to family. Fallback to 'unknown' if not identifiable.
    
    Returns:
        tuple: (raw_color, color_family)
    """
    if not isinstance(text, str):
        return "unknown", "unknown"
        
    text_lower = text.lower()
    
    # Sort keys by length in descending order to match multi-word phrases (e.g., 'navy blue') before single words ('blue')
    sorted_keys = sorted(COLOR_FAMILY_MAP.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
            return key, COLOR_FAMILY_MAP[key]
            
    return "unknown", "unknown"

def main():
    print("🚀 Initializing Ingestion Pipeline...")
    
    # 1. Connect to Qdrant Server
    try:
        if QDRANT_URL:
            print(f"Connecting to Qdrant Cloud at {QDRANT_URL}...")
            qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            print(f"Connecting to local Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
            qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # Check connection status
        collections = qdrant_client.get_collections()
        print("Connected to Qdrant successfully!")
    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        if not QDRANT_URL:
            print("Ensure the Qdrant Docker container is running (e.g., docker run -p 6333:6333 qdrant/qdrant)")
        return
        
    # 2. Load FashionCLIP Model
    print("Loading patrickjohncyh/fashion-clip model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    try:
        model = CLIPModel.from_pretrained("patrickjohncyh/fashion-clip").to(device)
        processor = CLIPProcessor.from_pretrained("patrickjohncyh/fashion-clip")
        print("FashionCLIP loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading FashionCLIP model: {e}")
        return

    # 3. Read products.csv
    print(f"Loading dataset from {PRODUCTS_CSV}...")
    try:
        products_df = pd.read_csv(PRODUCTS_CSV)
        print(f"Loaded {len(products_df)} products to ingest.")
    except Exception as e:
        print(f"❌ Error reading products.csv: {e}")
        return

    # 4. (Re)create Collection in Qdrant
    # Embedding dimensions for FashionCLIP (CLIP-ViT-B-32) is 512
    print(f"Setting up Qdrant collection '{COLLECTION_NAME}' (512 dimensions, Cosine distance)...")
    try:
        if qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
            print(f"Collection '{COLLECTION_NAME}' already exists. Deleting it for a fresh start...")
            qdrant_client.delete_collection(collection_name=COLLECTION_NAME)
            
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        )
        
        # Create payload indexes for fields we will filter on
        print("Creating payload keyword indexes...")
        for field in ["gender", "category", "occasion", "color_family"]:
            qdrant_client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD
            )
        print("Payload indexes created successfully!")
        print(f"Collection '{COLLECTION_NAME}' ready.")
    except Exception as e:
        print(f"❌ Error creating collection or indexes: {e}")
        return

    # 5. Process and Upsert Points
    points = []
    print("Encoding images and preparing payloads...")
    
    for idx, (_, row) in enumerate(products_df.iterrows()):
        product_id = row["id"]
        rel_img_path = row["image"]
        abs_img_path = os.path.join(WORKSPACE_ROOT, rel_img_path)
        
        # Color Extraction
        raw_color, color_family = extract_color_info(f"{row['name']} {row['description']}")
        
        # Image Embedding Generation
        embedding = None
        if os.path.exists(abs_img_path):
            try:
                image = Image.open(abs_img_path).convert("RGB")
                inputs = processor(images=image, return_tensors="pt").to(device)
                with torch.no_grad():
                    image_features = model.get_image_features(**inputs)
                    # Normalize embedding to unit sphere (L2 normalization)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    embedding = image_features[0].cpu().numpy().tolist()
            except Exception as img_err:
                print(f"⚠️ Error embedding image for product {product_id} at {abs_img_path}: {img_err}")
        else:
            print(f"⚠️ Image file not found for product {product_id} at {abs_img_path}")
            
        if embedding is None:
            # Fallback to zero vector if image is missing/corrupted so pipeline doesn't crash completely
            print(f"⚠️ Fallback to zero vector for {product_id}")
            embedding = [0.0] * 512
            
        # Structure the payload
        payload = {
            "id": product_id,
            "name": row["name"],
            "brand": row["brand"],
            "price_inr": int(row["price_inr"]),
            "gender": row["gender"],
            "wear_type": row["wear_type"],
            "category": row["category"],
            "category_label": row["category_label"],
            "occasion": row["occasion"],
            "tags": [tag.strip() for tag in str(row["tags"]).split(";")] if pd.notna(row["tags"]) else [],
            "raw_color": raw_color,
            "color_family": color_family,
            "image_path": rel_img_path
        }
        
        # Generate stable UUID for Qdrant using product ID
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, product_id))
        
        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        ))
        
        if (idx + 1) % 10 == 0 or (idx + 1) == len(products_df):
            print(f"Processed {idx + 1}/{len(products_df)} items...")

    # Upsert points to Qdrant
    print(f"Upserting {len(points)} points into Qdrant collection...")
    try:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print("🎉 Ingestion Pipeline completed successfully!")
    except Exception as e:
        print(f"❌ Error upserting points to Qdrant: {e}")

if __name__ == "__main__":
    main()
