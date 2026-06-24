import sys
import os

# Adjust sys.path to run the script from the root workspace folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.recommendation.assistant import FashionAssistant
from backend.recommendation.test_engine import print_outfit

def main():
    print("🧪 Running Conversational Fashion Assistant Verification Tests...")
    
    try:
        assistant = FashionAssistant()
        print("✅ Fashion Assistant initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize assistant: {e}")
        return

    # --- Test Case 1: Natural Language Query & Rationale Generation ---
    test_query = "I am a guy looking for a smart casual outfit for an office meeting."
    print(f"\nQuerying: '{test_query}'")
    
    try:
        recommendation = assistant.recommend_from_chat(test_query)
        if "error" in recommendation:
            print(f"❌ Test Failed: {recommendation['error']}")
            if "parsed_intent" in recommendation:
                print(f"Parsed Intent: {recommendation['parsed_intent']}")
        else:
            print("✅ Test Passed! Assistant generated complete recommendation:")
            print(f"Parsed Intent: {recommendation['parsed_intent']}")
            print_outfit(recommendation)
    except Exception as e:
        print(f"❌ Exception occurred during recommendation pipeline: {e}")
        import traceback
        traceback.print_exc()

    # --- Test Case 2: Validation Check on Invalid Occasion ---
    print("\n------------------------------------------------")
    print("Test Case 2: Testing Post-Parsing Allowed Occasion Validation")
    test_query_invalid = "I need a dress for a fancy business dinner party."
    print(f"Querying: '{test_query_invalid}'")
    
    try:
        intent = assistant.parse_user_query(test_query_invalid)
        print(f"Parsed Intent: {intent}")
        occasion = intent.get("occasion")
        print(f"Parsed Occasion: {occasion}")
        
        # Valid occasions list
        from backend.recommendation.assistant import ALLOWED_OCCASIONS
        if occasion is None or occasion in ALLOWED_OCCASIONS:
            print("✅ Test Passed! Invalid occasion was successfully validated/normalized (set to allowed list or null).")
        else:
            print(f"❌ Test Failed! Invalid occasion '{occasion}' bypassed validation filters.")
    except Exception as e:
        print(f"❌ Exception during parsing validation: {e}")

if __name__ == "__main__":
    main()
