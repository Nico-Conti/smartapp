import json
from google.genai import types, Client

# --- Schema Definitions ---

# Define the schema for an individual item (e.g., "shirt", "relaxed")
item_schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "tag": types.Schema(type=types.Type.STRING, description="The descriptive item tag (e.g., shirt, sweater)."),
        "fit": types.Schema(type=types.Type.STRING, description="A description of the appropriate fit (e.g., relaxed, fitted).")
    },
    required=["tag", "fit"]
)

# Define the schema for a category (e.g., "top")
category_schema = types.Schema(
    type=types.Type.OBJECT,
    description="A collection of item suggestions for a specific clothing category. If accessory limit to sunglasses, caps/hats or simple jewelry.",
    properties={
        "color_palette": types.Schema(type=types.Type.STRING, description="A specific color or color description (e.g., 'sky blue', 'dark indigo')."),
        "pattern": types.Schema(type=types.Type.STRING, description="A specific pattern (e.g., 'solid', 'striped', 'gingham')."),
        "items": types.Schema(type=types.Type.ARRAY, items=item_schema, description="A list of specific items for this category.")
    },
    required=["color_palette", "pattern", "items"]
)

# Define the main outfit_schema
outfit_schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "top": category_schema,
        "bottom": category_schema,
        "dresses": category_schema,
        "outerwear": category_schema,
        "swimwear": category_schema,
        "shoes": category_schema,
        "accessories": category_schema,
        "message": types.Schema(type=types.Type.STRING, description="A message for non-fashion related inquiries. MUST ONLY be present for guardrail messages.")
    },
)

# --- 3. System Prompt and Guardrail ---

SYSTEM_PROMPT = """
You are an expert fashion stylist AI. Your task is to receive a user's request for an outfit and return a structured JSON object that complies with the provided response_schema. You should not consider any external hard constraints (like specific item color/brand) as those will be applied later in the database query. Focus only on providing a stylish and cohesive outfit plan based on the user's request and general preferences.

GUARDRAIL: If the user's request is offensive towards any ethnicity, contains hatespeech or is in any way offensive towards anybody, you MUST immediately stop and return the following JSON object ONLY:
{'message': "I cannot fulfill this request. Content that promotes hate speech, discrimination, or is offensive toward any group or individual violates my safety policy and is strictly forbidden."}

GUARDRAIL: If the user's request is NOT related to fashion, outfits, styles, or clothing, you MUST immediately stop and return the following JSON object ONLY:
{'message': "I'm here to help with fashion-related inquiries. Please ask me about outfits, styles, or clothing recommendations"}

The final output MUST be a single JSON object and nothing else.
\n*** CRITICAL INSTRUCTION ***\n
the field 'message' MUST BE PRESENT ONLY if a guardrail triggers.
\n**************************
"""

FASHION_CATEGORIES = ['top', 'bottom', 'dresses', 'outerwear', 'swimwear', 'shoes', 'accessories']

# --- 4. Core Functions ---
def generate_outfit_plan(CLIENT: Client, MODEL_NAME: str, user_prompt: str, user_preferences: dict | None, gender: str) -> dict:
    """
    Sends the user prompt to Gemini for stylistic suggestions.
    NOTE: hard_constraints are EXCLUDED from the prompt sent to the LLM.
    Returns the raw parsed JSON dictionary.
    """
    try:
        
        user_request_block = (
            "*** USER REQUEST ***\n"
            f"{user_prompt}"
            "\n**************************\n"
        )
        
        # Normalize the prompt for conflict filtering
        normalized_prompt = user_prompt.lower()

        preference_string = ""
        
        if user_preferences or gender:
            preferences = []

            # --- PREFERENCE FILTERING (Soft Suggestions) ---
            if user_preferences and user_preferences.get('favorite_color'):
                preferences.append(f"favorite color: {user_preferences['favorite_color']}")
            
            if user_preferences and user_preferences.get('favorite_material'):
                preferences.append(f"favorite material: {user_preferences['favorite_material']}")

            if user_preferences and user_preferences.get('favorite_brand'):
                preferences.append(f"favorite brand: {user_preferences['favorite_brand']}")
            # --- END PREFERENCE FILTERING ---
                
            gender_block = ""
            if gender:
                gender_block = (
                    "\n*** USER GENDER ***\n"
                    f"When selecting the outfit plan, note that the gender of the user is: {gender}.\n"
                )
                
            if preferences:
                preference_string = (
                    gender_block +
                    "\n*** USER PREFERENCES (SOFT SUGGESTIONS) ***\n"
                    "When selecting the outfit plan, keep the following user preferences in mind: "
                    f"{', '.join(preferences)}."
                    "\n*** CRITICAL INSTRUCTION: STYLISH INTEGRATION ***\n"
                    "Treat all provided user preferences (color, material, brand) as strong suggestions to be **integrated tastefully** into the final ensemble, not as mandatory rules for every single item. Style and outfit cohesion are paramount."
                    "Specifically:\n"
                    "1. **Color:** **DO NOT** enforce the favorite color on *every* item. Use it sparingly to create a cohesive, balanced look (e.g., one or two black items if the preference is black, with the rest being complementary colors)."
                    "2. **Material/Brand:** **DO NOT** enforce the preferred material or brand on *every* item. More importantly, **NEVER** recommend a material that clashes with the user's request context (e.g., recommending wool for a beach outfit, even if it is a user preference)."
                    "Ensure all returned descriptions are **coherent** and make up a **well-structured, complete outfit**."
                    "\n**************************"
                )
            else:
                preference_string = gender
        # The final prompt sent to the LLM deliberately EXCLUDES hard_constraints
        full_prompt_for_llm = user_request_block + preference_string

        response = CLIENT.models.generate_content(
            model=MODEL_NAME,
            contents=[full_prompt_for_llm],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=outfit_schema
            )
        )
        return response.parsed
    except Exception as e:
        print("EXCEPTION: ", e)
        return {'message': 'Failed to generate outfit plan.'}

def parse_outfit_plan(json_plan: dict, hard_constraints: dict | None) -> list[dict]:
    """
    Transforms the structured JSON plan (output of the LLM) into a simplified 
    list of item descriptions for the Embedding Component, merging in the 
    database hard constraints.
    """
    
    # Check if a fashion plan was successfully generated 
    has_fashion_categories = any(key in json_plan for key in FASHION_CATEGORIES)
    
    # Scenario 1: Guardrail fired correctly (only 'message' key present)
    if 'message' in json_plan and not has_fashion_categories:
        return [json_plan] 
    
    response_list = []
    
    # Iterate through each clothing category
    for category_name, category_data in json_plan.items():
        if category_name == 'message':
            continue 
            
        # Get constraints for this specific category (e.g., {"top": {"color": "black"}})
        # This is where the hard constraints are introduced into the processing pipeline
        constraints_for_category = hard_constraints.get(category_name, {}) if hard_constraints else {}
            
        if isinstance(category_data, dict) and 'items' in category_data:
            
            # Extract attributes from LLM (these are soft, stylistic suggestions)
            category_color = category_data.get('color_palette', '').strip()
            pattern = category_data.get('pattern', '').strip()
            
            # Iterate through individual items in the category
            for item in category_data['items']:
                
                item_tag = item.get('tag', '').strip()
                item_fit = item.get('fit', '').strip()
                
                # Combine LLM's stylistic suggestions into a single description for the embedding search
                parts = [item_tag, item_fit, category_color, pattern]
                item_desc = " ".join(filter(None, parts)).strip()
                
                # The final list contains the LLM's stylistic prompt AND the hard constraints for database filtering
                response_list.append({
                    'category': category_name,
                    'description': item_desc, 
                    'hard_constraints': constraints_for_category # <-- Database MUST enforce these
                })
    
    # Fallback for empty list
    if not response_list and 'message' in json_plan:
         return [{'message': json_plan['message']}]
         
    return response_list

#ONLY USED FOR LOCAL AND TARGETED TESTING
if __name__ == '__main__':
    # Add minimal required imports for standalone testing
    import os
    from dotenv import load_dotenv
    from google import genai
    load_dotenv()
    
    # Initialize Client for testing purposes
    try:
        TEST_CLIENT = genai.Client()
        TEST_MODEL = 'gemini-2.5-flash'
    except Exception as e:
        print(f"Could not initialize TEST_CLIENT (check API Key): {e}")
        exit()
        
    # --- TEST SETUP ---
    # Soft Preferences (Gemini sees these)
    test_prompt = "I need a men's outfit for a fancy cocktail party, but make it modern."
    test_preferences = {'favorite_color': 'navy', 'favorite_material': 'Silk'}
    
    # Hard Constraints (Gemini does NOT see these, they are applied here)
    test_hard_constraints = {
        "top": {"color": "black", "material": "velvet", "size": "L"},
        "shoes": {"brand": "Gucci"}
    }
    
    print(f"--- Sending Prompt: '{test_prompt}' ---")
    
    # 1. Get the plan from the LLM (LLM only sees navy/silk preference)
    outfit_json = generate_outfit_plan(TEST_CLIENT, TEST_MODEL, test_prompt, user_preferences=test_preferences, hard_constraints=test_hard_constraints, gender="Male")
    
    print("\n--- Raw LLM Response (Structured JSON) ---")
    print(json.dumps(outfit_json, indent=2))
    
    # 2. Parse the plan and merge hard constraints
    parsed_items = parse_outfit_plan(outfit_json, hard_constraints=test_hard_constraints)
    
    print("\n--- Parsed Item List (Ready for Embedding/DB Query) ---")
    # Check that 'top' and 'shoes' items now contain the 'hard_constraints' key
    print(json.dumps(parsed_items, indent=2))
    
    print("\n" + "="*50 + "\n")