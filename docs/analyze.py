import pandas as pd
import os

# Set paths relative to the docs directory
DATASET_DIR = "../"
products_df = pd.read_csv(os.path.join(DATASET_DIR, "products.csv"))
outfits_df = pd.read_csv(os.path.join(DATASET_DIR, "outfits.csv"))

print("--- PRODUCTS COLUMNS ---")
print(products_df.columns.tolist())
print("\n--- PRODUCTS INFO ---")
print(products_df.info())

print("\n--- CATEGORY VALUE COUNTS ---")
print(products_df["category"].value_counts())
print("\n--- CATEGORY LABEL VALUE COUNTS ---")
if "category_label" in products_df.columns:
    print(products_df["category_label"].value_counts())
else:
    print("category_label column not found in products.csv")

print("\n--- PRODUCTS NULL COUNTS ---")
print(products_df.isnull().sum())

print("\n--- OUTFITS COLUMNS ---")
print(outfits_df.columns.tolist())
print("\n--- OUTFITS INFO ---")
print(outfits_df.info())

print("\n--- OUTFITS NULL COUNTS ---")
print(outfits_df.isnull().sum())

print("\n--- UNIQUE VALUES FOR METADATA ---")
for col in ['gender', 'wear_type', 'occasion']:
    if col in products_df.columns:
        print(f"\n{col}:")
        print(products_df[col].value_counts())

# Let's count image files too
images_dir = os.path.join(DATASET_DIR, "images")
image_count = 0
for root, dirs, files in os.walk(images_dir):
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image_count += 1
print(f"\nTotal images found in {images_dir}: {image_count}")
