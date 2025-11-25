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

# Defines the structure for hard constraints applied to a single item category.
# (This was likely the original 'constraint_item_schema')
constraint_item_schema = types.Schema(
    type=types.Type.OBJECT,
    description="Any color, material, or brand constraints specified by the user for this category.",
    properties={
        "color": types.Schema(type=types.Type.STRING),
        "material": types.Schema(type=types.Type.STRING),
        "brand": types.Schema(type=types.Type.STRING),
    },
)

# Defines the primary schema for managing the conversational state
input_gathering_schema = types.Schema(
    type=types.Type.OBJECT,
    description="Schema used for multi-turn conversations to gather required information before generating the final outfit plan.",
    properties={
        "status": types.Schema(type=types.Type.STRING, description="The current status. Must be 'AWAITING_INPUT' if max_budget or sufficient hard_constraints are missing, or 'READY_TO_GENERATE' if all necessary inputs are gathered."),
        "missing_info": types.Schema(type=types.Type.STRING, description="A polite, conversational TEXTUAL message asking the user for the specific missing information (e.g., 'What is your maximum budget and what constraints do you have for the top?') This is the message presented to the user."),
        "max_budget": types.Schema(type=types.Type.NUMBER, description="The maximum budget (€) extracted from the conversation history so far. Must be 0 if not yet specified or ambiguous."),
        "hard_constraints": types.Schema(
            type=types.Type.OBJECT,
            description="All extracted hard constraints (color, material, brand) organized by category (top, bottom, shoes, etc.).",
            properties={
                "top": constraint_item_schema,
                "bottom": constraint_item_schema,
                "outerwear": constraint_item_schema,
                "shoes": constraint_item_schema,
                "accessories": constraint_item_schema,
            }
        ),
        "message": types.Schema(type=types.Type.STRING, description="field that must contain ONLY the error message if a guardrail condition triggers"),
    },
    #required=["status", "missing_info", "max_budget", "hard_constraints"]
    required=["status"]
)

# 1. New Schema for ONLY the Outfit Categories (The nested 'outfit_plan')
outfit_categories_schema = types.Schema(
    type=types.Type.OBJECT,
    description="Contains the suggested clothing items and accessories, excluding metadata like budget and constraints.",
    properties={
        "top": category_schema,
        "bottom": category_schema,
        "dresses": category_schema,
        "outerwear": category_schema,
        "swimwear": category_schema,
        "shoes": category_schema,
        "accessories": category_schema,
    },
)

# 2. Revised Main Outfit Generation Schema (The LLM's full output)
# This schema separates the outfit plan, budget, and constraints at the top level.
outfit_schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        # The nested categories container
        "outfit_plan": outfit_categories_schema,

        # Metadata fields at the top level
        "max_budget": types.Schema(
            type=types.Type.NUMBER,
            description="The maximum budget (€ or $) extracted from the conversation history. Must be 0 if not yet specified or ambiguous."
        ),
        "hard_constraints": types.Schema(
            type=types.Type.OBJECT,
            description="All extracted hard constraints organized by category.",
            properties={
                "top": constraint_item_schema,
                "bottom": constraint_item_schema,
                "outerwear": constraint_item_schema,
                "shoes": constraint_item_schema,
                "accessories": constraint_item_schema,
            }
        ),
        "message": types.Schema(
            type=types.Type.STRING,
            description="A message for non-fashion related inquiries. MUST ONLY be present for guardrail messages."
        )
    },
)

# --- 3. System Prompt and Guardrail ---
TEXTUAL_SYSTEM_PROMPT = """
You are an expert conversational fashion stylist AI. Your primary goal is to first gather all necessary information and then provide a structured outfit plan.

[STEP 1: INFORMATION GATHERING (Use InputGatheringSchema)]

Analyze the ENTIRE conversation history.

Determine if a 'max_budget' (a numerical value in € or $) has been explicitly provided by the user. Hard constraints (brand, color, material) are OPTIONAL for generation.

If the user explicitly states that he/she does not care about a specific budget, set the 'max_budget' to 100000, set the 'status' to 'READY_TO_GENERATE'

If the 'max_budget' is missing, set the 'status' to 'AWAITING_INPUT' and provide a specific, conversational question in the 'missing_info' field. The question MUST ask for the budget, and it should also politely ask if the user has any OPTIONAL hard constraints.

Make sure that, if the user's specifies any constraints, that they are applied ONLY TO THE SPECIFIED CLOTHING ITEMS.

If the 'max_budget' is present, set the 'status' to 'READY_TO_GENERATE'.

[STEP 2: OUTFIT GENERATION (Use OutfitSchema)]
5. ONLY if the 'status' would be 'READY_TO_GENERATE', you MUST switch modes and generate the final outfit plan using the standard OutfitSchema. The final output MUST NOT contain the status/missing_info fields in this case. The final output should be a full outfit by default, but you should include only the clothing itmes requested by the user if any. DO NOT INCLUDE MORE THAN 1 ITEM FOR EACH 'category_schema' UNLESS STRICTLY NECESSARY. If constraints are missing, assume flexibility and generate a well-curated outfit that fits the occasion and budget. 

[CONSTRAINT EXTRACTION]

Extract all budget and hard constraints provided by the user in the history and populate the 'max_budget' and 'hard_constraints' fields, even if the status is 'AWAITING_INPUT'.
Do not make up constraints, just extract constraints if the user explicitly inputs them.

GUARDRAIL: If the user's request is offensive towards any ethnicity, contains hatespeech or is in any way offensive towards anybody, you MUST immediately stop and return the following JSON object ONLY:
{'status': 'Guardrail', 'message': "I cannot fulfill this request. Content that promotes hate speech, discrimination, or is offensive toward any group or individual violates my safety policy and is strictly forbidden."}

GUARDRAIL: If the user's request is NOT related to fashion, outfits, styles, or clothing, you MUST immediately stop and return the following JSON object ONLY:
{'status': 'Guardrail', 'message': "I'm here to help with fashion-related inquiries. Please ask me about outfits, styles, or clothing recommendations"}
"""


IMAGE_SYSTEM_PROMPT = """
You are an expert conversational fashion stylist AI. Your primary goal is to first gather all necessary information (Budget AND Intent) and then provide a structured outfit plan.

[STEP 1: INFORMATION GATHERING (Use InputGatheringSchema)]

Analyze the ENTIRE conversation history and the attached image.

Determine if the following two pieces of information are explicitly present:
a. Determine if a 'max_budget' (a numerical value in € or $) has been explicitly provided by the user. Hard constraints (brand, color, material) are OPTIONAL for generation.

If the user explicitly states that he/she does not care about a specific budget, set the 'max_budget' to 100000

b. The user's 'image_intent' (i.e., what they want you to do with the image, such as "complete the outfit," "find similar style," "suggest an alternative"). (MANDATORY)

If the 'max_budget' or the 'user's intent' is missing, set the 'status' to 'AWAITING_INPUT' and provide a specific, conversational question in the 'missing_info' field. The question MUST ask for the budget and the user's intent, and it should also politely ask if the user has any OPTIONAL hard constraints.

If BOTH the 'max_budget' and the 'image_intent' are present, set the 'status' to 'READY_TO_GENERATE'.

[STEP 2: OUTFIT GENERATION (Use OutfitSchema)]
a. If the intent was to find matching items or complete the outfit shown, generate only the complementary items required to form a full, cohesive look.
b. If the intent was to find an outfit in the same style or aesthetic as the image, generate a full, coherent outfit that captures the overall fashion sense of the image.
5. ONLY if the 'status' would be 'READY_TO_GENERATE', you MUST switch modes and generate the final outfit plan using the standard OutfitSchema. The final output MUST NOT contain the status/missing_info fields in this case. The final output should be a full outfit by default, but you should include only the clothing itmes requested by the user if any. DO NOT INCLUDE MORE THAN 1 ITEM FOR EACH 'category_schema' UNLESS STRICTLY NECESSARY. If constraints are missing, assume flexibility and generate a well-curated outfit that fits the occasion and budget. 


[CONSTRAINT EXTRACTION]

Extract all budget and hard constraints provided by the user in the history. If the user explicitly asks for an item with a feature that matches the image (e.g., "same color"), you MUST analyze the image to determine the feature's value and use that specific, descriptive value in the 'description' field, NOT in the 'hard_constraints' field. DO NOT use literal phrases like "same as in the picture."

GUARDRAIL: If the user's request is offensive towards any ethnicity, contains hatespeech or is in any way offensive towards anybody, you MUST immediately stop and return the following JSON object ONLY:
{'status': 'Guardrail', 'message': "I cannot fulfill this request. Content that promotes hate speech, discrimination, or is offensive toward any group or individual violates my safety policy and is strictly forbidden."}

GUARDRAIL: If the user's request is NOT related to fashion, outfits, styles, or clothing, you MUST immediately stop and return the following JSON object ONLY:
{'status': 'Guardrail', 'message': "I'm here to help with fashion-related inquiries. Please ask me about outfits, styles, or clothing recommendations"}

The final output MUST be a single JSON object and nothing else.
\n*** CRITICAL INSTRUCTION \n
the field 'message' MUST BE PRESENT ONLY if a guardrail triggers.
\n***********************
"""

FASHION_CATEGORIES = ['top', 'bottom', 'dresses', 'outerwear', 'swimwear', 'shoes', 'accessories']


# def build_dynamic_system_prompt(base_prompt, partial_list):

#     dynamic_prompt = base_prompt
#     item_list = ", ".join([f"'{item}'" for item in partial_list])

#     constraint_injection = (
#                 f"\n\n*** PARTIAL OUTFIT CRITICAL INSTRUCTION ***\n"
#                 f"Since this is a partial generation request, you **MUST** only include the following categories AND NOTHING ELSE in the JSON output: [{item_list}]. "
#                 f"You MUST NOT include any other categories (like 'top', 'bottom', etc.) in the final JSON object keys. "
#                 f"\n*********************************************"
#             )
#     dynamic_prompt = dynamic_prompt.replace("\n*** CRITICAL INSTRUCTION ***\n", constraint_injection + "\n*** CRITICAL INSTRUCTION ***\n")
#     return dynamic_prompt

# --- 4. Core Functions ---
# def generate_outfit_plan(CLIENT: Client, MODEL_NAME: str, user_prompt: str, image_data:tuple[str, str] | None, user_preferences: dict | None, gender: str | None) -> dict:
#     """
#     Sends the user prompt to Gemini for stylistic suggestions.
#     NOTE: hard_constraints are EXCLUDED from the prompt sent to the LLM.
#     Returns the raw parsed JSON dictionary.
#     """
#     try:

#         #MOCK-UP RIGHT NOW, FOR THE FINAL IMPLEMENTATION SINCE THEY WANT TO MAKE IT ALL CHAT BASED
#         #IF THE USER IS NOT LOGGED IN AND DOES NOT SPECIFY HIS/HER GENDER IN THE INITIAL QUERY
#         #GEMINI NEEDS TO ASK THE USER FOR MORE DETAILS, INCLUDING THE GENDER
#         if gender is None:
#             gender = "male"
        
#         if image_data is None:
#             user_request_block = (
#                 "*** USER REQUEST ***\n"
#                 f"{user_prompt}"
#                 "\n**************************\n"
#             )
#         else:
#             image_data_str = f"Image Data: {image_data[0]}, MIME Type: {image_data[1]}"
#             user_request_block = (
#                 "*** USER REQUEST ***\n"
#                 f"{user_prompt} {image_data_str}" # Concatenate the strings
#                 "\n**************************\n"
#             )

#         preference_string = ""
        
#         if user_preferences or gender:
#             preferences = []

#             # --- PREFERENCE FILTERING (Soft Suggestions) ---
#             if user_preferences and user_preferences.get('favorite_color'):
#                 preferences.append(f"favorite color: {user_preferences['favorite_color']}")
            
#             if user_preferences and user_preferences.get('favorite_material'):
#                 preferences.append(f"favorite material: {user_preferences['favorite_material']}")

#             if user_preferences and user_preferences.get('favorite_brand'):
#                 preferences.append(f"favorite brand: {user_preferences['favorite_brand']}")
#             # --- END PREFERENCE FILTERING ---
                
#             gender_block = ""
#             if gender:
#                 gender_block = (
#                     "\n*** USER GENDER ***\n"
#                     f"When selecting the outfit plan, note that the gender of the user is: {gender}.\n"
#                 )
                
#             if preferences:
#                 preference_string = (
#                     gender_block +
#                     "\n*** USER PREFERENCES (SOFT SUGGESTIONS) ***\n"
#                     "When selecting the outfit plan, keep the following user preferences in mind: "
#                     f"{', '.join(preferences)}."
#                     "\n*** CRITICAL INSTRUCTION: STYLISH INTEGRATION ***\n"
#                     "Treat all provided user preferences (color, material, brand) as strong suggestions to be **integrated tastefully** into the final ensemble, not as mandatory rules for every single item. Style and outfit cohesion are paramount."
#                     "Specifically:\n"
#                     "1. **Color:** **DO NOT** enforce the favorite color on *every* item. Use it sparingly to create a cohesive, balanced look (e.g., one or two black items if the preference is black, with the rest being complementary colors)."
#                     "2. **Material/Brand:** **DO NOT** enforce the preferred material or brand on *every* item. More importantly, **NEVER** recommend a material that clashes with the user's request context (e.g., recommending wool for a beach outfit, even if it is a user preference)."
#                     "Ensure all returned descriptions are **coherent** and make up a **well-structured, complete outfit**."
#                     "\n**************************"
#                 )
#             else:
#                 preference_string = gender
#         # The final prompt sent to the LLM deliberately EXCLUDES hard_constraints
#         full_prompt_for_llm = user_request_block + preference_string

#         base_prompt = IMAGE_SYSTEM_PROMPT if image_data else TEXTUAL_SYSTEM_PROMPT

#         response = CLIENT.models.generate_content(
#             model = MODEL_NAME,
#             contents = [full_prompt_for_llm],
#             config = types.GenerateContentConfig(
#                 system_instruction = base_prompt,
#                 response_mime_type = "application/json",
#                 response_schema = outfit_schema
#             )
#         )

#         return response.parsed
    
#     except Exception as e:
#         print("EXCEPTION: ", e)
#         return {'message': 'Failed to generate outfit plan.'}


def generate_outfit_plan(
    client: Client, 
    model_name: str, 
    new_user_query: str, 
    chat_history: list, 
    image_data:tuple[str, str] | None,
    user_preferences: dict | None, 
    gender: str | None 
) -> dict:
    """
    Manages the multi-turn conversation flow, gathering constraints or generating the final outfit.
    """

    if gender is None:
            gender = "male"
        
    if image_data is None:
        user_request_block = (
            "*** USER REQUEST ***\n"
            f"{new_user_query}"
            "\n**************************\n"
        )
    else:
        image_data_str = f"Image Data: {image_data[0]}, MIME Type: {image_data[1]}"
        user_request_block = (
            "*** USER REQUEST ***\n"
            f"{new_user_query} {image_data_str}" # Concatenate the strings
            "\n**************************\n"
        )

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
            preference_string = gender_block
    # The final prompt sent to the LLM deliberately EXCLUDES hard_constraints
    full_prompt_for_llm = user_request_block + preference_string

    base_prompt = IMAGE_SYSTEM_PROMPT if image_data else TEXTUAL_SYSTEM_PROMPT

    # 1. Add the new user query to the history
    chat_history.append({"role": "user", "parts": [{"text": full_prompt_for_llm}]})
    
    # 2. First attempt: Use the Input Gathering Schema to check state and extract constraints
    try:
        # We always send the full history to maintain context
        response = client.models.generate_content(
            model = model_name,
            contents = chat_history,
            config = types.GenerateContentConfig(
                system_instruction = base_prompt,
                response_mime_type = "application/json",
                response_schema = input_gathering_schema # Target the state-management schema
            )
        )
        
        # This will be the parsed JSON from the InputGatheringSchema
        dialogue_state = response.parsed
        
    except Exception as e:
        print(f"Error during dialogue state check: {e}")
        return {'error': 'Failed to process dialogue state.'}

    # 3. Analyze the returned status
    if dialogue_state.get('status') == 'AWAITING_INPUT':
        # The model is asking for more information.
        # The application should display dialogue_state['missing_info'] to the user.
        
        # Add the model's textual prompt to the history for context in the next turn
        chat_history.append({"role": "model", "parts": [{"text": dialogue_state['missing_info']}]})
        
        return {
            'status': 'AWAITING_INPUT',
            'prompt_to_user': dialogue_state['missing_info'],
            'history': chat_history,
            'current_budget': dialogue_state.get('max_budget'),
            'current_constraints': dialogue_state.get('hard_constraints')
        }
        
    elif dialogue_state.get('status') == 'READY_TO_GENERATE':
        
        # All information is present. The system prompt instructs Gemini to switch modes,
        # but since we target the schema here, we need a SECOND, final API call 
        # specifically targeting the outfit_schema.
        
        # The final prompt in the history must instruct the model to generate the outfit JSON
        final_generation_prompt = chat_history + [{
            "role": "user", 
            "parts": [{"text": "All constraints are now provided. Please generate the final, complete outfit plan immediately using the OutfitSchema."}]
        }]
        
        try:
            # 4. Final attempt: Use the Outfit Schema
            final_response = client.models.generate_content(
                model = model_name,
                contents = final_generation_prompt,
                config = types.GenerateContentConfig(
                    system_instruction = base_prompt,
                    response_mime_type = "application/json",
                    response_schema = outfit_schema # Target the FINAL outfit schema
                )
            )
            
            final_data = final_response.parsed

            return {
                'status': 'Complete',
                'outfit_plan': final_data.get('outfit_plan'),
                'budget': final_data.get('max_budget'),
                'constraints': final_data.get('hard_constraints'),
                'history': final_generation_prompt 
            }
            
        except Exception as e:
            print(f"Error during final outfit generation: {e}")
            return {'error': 'Failed to generate final outfit plan.'}
            
    else:
        # Handles guardrail response or unexpected structure
        print(dialogue_state)
        return dialogue_state
    

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