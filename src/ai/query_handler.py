import json
from google.genai import types, Client

# --- Schema Definitions (From your notebook logic) ---

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
        "shoes": category_schema,
        "accessories": category_schema,
        "message": types.Schema(type=types.Type.STRING, description="A message for non-fashion related inquiries. MUST ONLY be present for guardrail messages.")
    },
)

# --- 3. System Prompt and Guardrail ---

SYSTEM_PROMPT = """
You are an expert fashion stylist AI. Your task is to receive a user's request for an outfit and return a structured JSON object that complies with the provided schema.

GUARDRAIL: If the user's request is offensive towards any ethnicity, contains hatespeech or is in any way offensive towards anybody, you MUST immediately stop and return the following JSON object ONLY:
{'message': "I cannot fulfill this request. Content that promotes hate speech, discrimination, or is offensive toward any group or individual violates my safety policy and is strictly forbidden."}

GUARDRAIL: If the user's request is NOT related to fashion, outfits, styles, or clothing, you MUST immediately stop and return the following JSON object ONLY:
{'message': "I'm here to help with fashion-related inquiries. Please ask me about outfits, styles, or clothing recommendations"}

The final output MUST be a single JSON object and nothing else.
"""

# --- 4. Core Functions ---

def generate_outfit_plan(CLIENT: Client, MODEL_NAME: str, user_prompt: str, user_preferences: dict | None, gender: str) -> dict:
    """
    Sends the user prompt to Gemini and enforces the structured JSON output.
    Returns the raw parsed JSON dictionary.
    """
    try:
        
        user_request_block = (
            "*** USER REQUEST ***\n"
            f"{user_prompt}"
            "\n**************************\n"
        )

        preference_string = ""
        if user_preferences:
            # Build a list of specific preferences to pass to the LLM
            preferences = []
            if user_preferences.get('favorite_color'):
                preferences.append(f"favorite color: {user_preferences['favorite_color']}")
            if user_preferences.get('favorite_material'):
                preferences.append(f"favorite material: {user_preferences['favorite_material']}")
            if user_preferences.get('favorite_brand'):
                preferences.append(f"favorite brand: {user_preferences['favorite_brand']}")
                
            if preferences:
                # Combine the preferences into a natural language sentence
                preference_string = (
                    "\n*** USER GENDER ***\n"
                    "When selecting the outfit plan, note that the gender of the user is: "
                    f"{', '.join(gender)}."
                    "\n*** USER PREFERENCES ***\n"
                    "When selecting the outfit plan, keep the following user preferences in mind: "
                    f"{', '.join(preferences)}."
                    "\n*** CRITICAL INSTRUCTION ***\n"
                    "**DO NOT** enforce the favorite color on *every* item. The **color_palette** field for each category should describe the item's specific color within a *cohesive, stylish* outfit. For example, if the favorite color is black, only one or two items might be black, with the others being complementary colors (e.g., white, grey, or charcoal)."
                    "Ensure all returned descriptions are **coherent** and make up a **well-structured, complete outfit**."
                    "\n**************************"
                )

        full_prompt_for_llm = user_request_block + preference_string
        # print(full_prompt_for_llm)

        response = CLIENT.models.generate_content(
            model=MODEL_NAME,
            contents=[full_prompt_for_llm],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=outfit_schema
            )
        )
        # print(response.parsed)
        # The .parsed property automatically gives you the JSON as a Python dict
        return response.parsed
    except Exception as e:
        print("EXCEPTION: ", e)
        return {'message': 'Failed to generate outfit plan.'}

def parse_outfit_plan(json_plan: dict) -> list[dict]:
    """
    Transforms the structured JSON plan (output of the LLM) into a simplified 
    list of item descriptions for the Embedding Component.
    """
    if 'message' in json_plan:
        # Pass the guardrail message straight through
        return [json_plan] 

    response_list = []
    
    # Iterate through each clothing category (top, bottom, shoes, etc.)
    for category_name, category_data in json_plan.items():
        if isinstance(category_data, dict) and 'items' in category_data:
            
            # Extract common attributes for this category
            color = category_data.get('color_palette', '').strip()
            pattern = category_data.get('pattern', '').strip()
            
            # Iterate through individual items in the category
            for item in category_data['items']:
                
                # Combine all descriptive attributes into a single query string
                item_desc = (
                    f"{item.get('tag', '')} {item.get('fit', '')} "
                    f"{color} {pattern}"
                ).strip()
                
                # The final list contains item descriptions and their category for retrieval
                response_list.append({
                    'category': category_name,
                    'description': item_desc
                })
    return response_list

#ONLY USED FOR LOCAL AND TARGETED TESTING
if __name__ == '__main__':
    
    # --- Test Case 1: Successful Fashion Query ---
    test_prompt = "give me an outfit that's appropriate for a night out with my friends, please notice that i am a man"
    #test_prompt = "I need a professional but comfortable outfit for a remote work day. Something minimal in darker colors."
    print(f"--- Sending Prompt: '{test_prompt}' ---")
    
    outfit_json = generate_outfit_plan(test_prompt)
    
    print("\n--- Raw LLM Response (Structured JSON) ---")
    print(json.dumps(outfit_json, indent=2))

    parsed_items = parse_outfit_plan(outfit_json)
    
    print("\n--- Parsed Item List (Ready for Embedding Component) ---")
    print(json.dumps(parsed_items, indent=2))
    
    print("\n" + "="*50 + "\n")