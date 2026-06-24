# Video Presentation Script & Outline
## Project: AI Fashion Outfit Recommendation System

This guide outlines a structured, professional script to help you record your **5–10 minute demonstration video**. Use this outline as a screen-by-screen guide while recording.

---

## ⏱️ Timeline Allocation Overview
1. **0:00 - 0:45 (45s)**: Introduction & Project Overview
2. **0:45 - 2:00 (75s)**: Dataset Understanding & Challenges
3. **2:00 - 3:15 (75s)**: System Architecture
4. **3:15 - 4:45 (90s)**: Core Design Decisions & Algorithms
5. **4:45 - 8:00 (195s)**: Live System Demonstration
6. **8:00 - 9:00 (60s)**: Key Challenges & Mitigations
7. **9:00 - 9:30 (30s)**: Future Extensions & Wrap-up

---

## 🎤 Script Section-by-Section

### Section 1: Introduction (0:00 - 0:45)
* **Visuals**: Show the Home page of your web application running on `http://localhost:3000` with the dark glassmorphic design and the live "Online" status indicator.
* **Talk Track**:
  > *"Hello, everyone. My name is [Your Name], and today I am demonstrating my submission for the Dare XAI AI Fashion Outfit Recommendation System. 
  > 
  > The goal of this project is to build an intelligent, context-aware styling assistant. The application consists of a conversational AI stylist chat, a filterable product catalog browser, and an interactive outfit canvas that displays complete, color-coordinated styling recommendations with explanations. Let's start by looking at the data."*

---

### Section 2: Dataset Understanding (0:45 - 2:00)
* **Visuals**: Show [dataset_analysis.md](file:///c:/Users/HP/Desktop/ML-TASK/docs/dataset_analysis.md) or open the CSV files (`products.csv` and `outfits.csv`).
* **Talk Track**:
  > *"Our dataset is divided into two parts:
  > First, we have `products.csv` which contains 68 unique fashion items from brands like Arrow, Titan, and Puma. We analyzed the category distribution and noticed it contains 47 highly granular sub-categories, which means our system must understand fashion relationships dynamically rather than using generic filters.
  > 
  > Second, we have `outfits.csv` containing 25 expert-curated outfits matching various themes and occasions like weddings, office work, and casual wear.
  > 
  > We observed two major dataset challenges:
  > 1. **Massive Rating Sparsity**: Over 36% of items lack rating scores, meaning standard collaborative filtering wouldn't work. We mitigated this by treating ratings as a secondary score boost.
  > 2. **Implicit Garment Rules**: Half of the expert outfits do not include bottomwear because they center on one-piece items like dresses, sarees, or suits. A naive algorithm that always recommends a top, bottom, and shoes would break here. We built category-based logical branches to handle this."*

---

### Section 3: System Architecture (2:00 - 3:15)
* **Visuals**: Show the repository structure or draw attention to the folder layout (`backend/` and `frontend/`).
* **Talk Track**:
  > *"To support this project, I engineered a decoupled, full-stack monorepo:
  > * **Frontend**: Built with **Next.js 16 (App Router)** and styled using custom **Vanilla CSS** to deliver a premium, glassmorphic dark-theme dashboard.
  > * **Backend**: Developed with **FastAPI** to expose fast, typed endpoints.
  > * **Database**: Powered by **Qdrant Cloud Vector Database** for sub-second visual similarity retrieval.
  > * **ML Models**: We use **FashionCLIP** to encode text queries and image files into a shared 512-dimension space, and the **Groq API** running `llama-3.3-70b-versatile` to handle conversational intent parsing and generate stylist rationales."*

---

### Section 4: Key Design Decisions & Approach (3:15 - 4:45)
* **Visuals**: Open [engine.py](file:///c:/Users/HP/Desktop/ML-TASK/backend/recommendation/engine.py) showing the `RecommendationEngine` class.
* **Talk Track**:
  > *"Here are the core technical decisions that drive the system:
  > 1. **Two-Stage Recommendation Engine**: When a product is selected, the engine checks if it exists in any expert-curated lookbook outfits (Stage 1). If found, it returns that curated look. If not, it falls back to an AI-composed vector search (Stage 2) using FashionCLIP to retrieve compatible coordinate slots from Qdrant.
  > 2. **Color Clashing & Monochromatic Rules**: To prevent clash colors, Stage 2 blocks matching colors for secondary items, except for classic neutrals like black and denim blue.
  > 3. **Chat-to-Canvas State Sync**: We implemented a state-locking mechanism. When the chat bot suggests an outfit, clicking 'Load in Canvas' locks that exact recommendation in place rather than triggering a re-fetch, which might otherwise load a different look.
  > 4. **Graceful Out-of-Catalog Deflection**: If a user asks for an item not in our catalog, the vector search finds the closest match, and our updated LLM prompt instructs the stylist to explain the deviation gracefully."*

---

### Section 5: Live System Demonstration (4:45 - 8:00)
* **Visuals**: Switch to the browser and perform these actions live:

#### Demo Step A: The Product Catalog Browser
* Click **Product Catalog** tab.
* Toggle filters (Men, Women, Casual, Office).
* Search for *"Arrow"*. Click a shirt.
* Show the **Outfit Canvas** on the right load the coordinates, color harmony chips, total price, and the stylist note. Highlight the **✨ Lookbook Curated** badge.

#### Demo Step B: Lookbook Curated Chat Match
* Click **AI Assistant Chat** tab.
* Type: *"I am a guy looking for a smart casual outfit for an office meeting."*
* Send and show the generated card with the **Navy tailored suit** theme.
* Click **Load in Canvas** and show the canvas loading the exact same items.

#### Demo Step C: AI Vector Matched Chat Match
* In the chat, type: *"I need a smart casual Zara blazer for men."*
* Show the bot loading the Zara blazer outfit card with the **AI Filtered** badge.
* Click **Load in Canvas**. Point to the **🤖 AI Vector Matched** badge on the canvas.

#### Demo Step D: Graceful Out-of-Catalog Deviation
* In the chat, type: *"I need a yellow cocktail dress."*
* Show the bot returning the closest match (the black Ruched Asymmetrical Dress) and show the generated rationale:
  > *"We don't have a yellow dress in our catalog, so I styled this classic black dress from our lookbook..."*
* Highlight how cleanly the LLM handles the catalog limitation.

---

### Section 6: Challenges & Mitigations (8:00 - 9:00)
* **Visuals**: Show [main.py](file:///c:/Users/HP/Desktop/ML-TASK/backend/main.py) or the terminal console.
* **Talk Track**:
  > *"During development, we solved several interesting issues:
  > * **Data Normalization**: Brand names like 'ARROW' and 'Arrow' had inconsistent casing. We normalized all keys to lowercase before ingestion.
  > * **Image Static Paths**: Resolved a NameError on the backend to dynamically serve and mount the catalog image files.
  > * **Git & Secrets Management**: Confirmed that our `.env` API keys are securely excluded from Git tracking via a custom root `.gitignore`, while packaging standard dependencies in `requirements.txt` to support smooth monorepo builds on Railway."*

---

### Section 7: Future Improvements & Wrap-up (9:00 - 9:30)
* **Visuals**: Show the front page of the dashboard again.
* **Talk Track**:
  > *"If I had more time, I would expand this in three areas:
  > 1. **Graph-based Recommendation**: Using graph neural networks (GNNs) to model outfits as networks where items are nodes and compatibility is represented by edges.
  > 2. **Visual Feature Extraction**: Extracting dominant color hexes directly from product images using OpenCV K-Means clustering.
  > 3. **Personalized User Profiles**: Tracking purchase history and age demographics to rank and weight recommendations.
  > 
  > Thank you for your time. The code, documentation, and unit tests are fully published in the private repository."*

---
