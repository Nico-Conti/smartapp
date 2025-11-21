import os
import logging
from google import genai
import torch
from supabase import create_client, Client
from transformers import CLIPProcessor, CLIPModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import custom modules
from src.ai.preferences_management import get_user_preferences
from src.ai.constraints_management import get_user_constraints
from src.ai.query_handler import generate_outfit_plan, parse_outfit_plan
from src.ai.query_embedder import get_text_embedding_vector 
from src.ai.outfit_retrieval_logic import search_product_candidates_with_vector_db
from src.ai.assemble_outfit import get_outfit, select_final_outfit_and_metrics
from src.ai.get_explanations import explain_selected_outfit

# --- 1. Global Initialization (Loaded only ONCE when the server starts) ---

# Load environment variables (like the GEMINI_API_KEY)
load_dotenv()

SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Handle environment variables missing: Critical, must stop.
    logging.critical("Supabase credentials (SUPABASE_URL, SUPABASE_KEY) are missing.")
    raise ValueError("Supabase credentials must be set in the environment or .env file.")
    
# 1. Supabase Client Initialization
try:
    SUPABASE_CLIENT: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Optional: Perform a small check query here to ensure connectivity (e.g., SELECT 1)
    logging.info("✅ Supabase client initialized successfully.")
except Exception as e:
    # Handle Supabase connection failure: Critical, must stop.
    logging.critical(f"❌ Error initializing Supabase client: {e}", exc_info=True)
    # Reraise the exception to stop the server process from starting
    raise ConnectionError("Failed to connect to Supabase.") from e

# 2. Gemini Client Initialization
try:
    GEMINI_CLIENT = genai.Client()
    logging.info("✅ Gemini client initialized successfully.")
except Exception as e:
    # Handle Gemini client initialization failure: Critical, must stop.
    logging.critical(f"❌ Error initializing Gemini client: {e}", exc_info=True)
    # Reraise the exception to stop the server process from starting
    raise RuntimeError("Failed to initialize the Google Gemini Client.") from e

GEMINI_MODEL_NAME = 'gemini-2.0-flash'

# 3. CLIP Model Initialization (Heavy/Critical Resource)
CLIP_MODEL_NAME = "patrickjohncyh/fashion-clip"
try:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    MODEL = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
    PROC = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME, use_fast=True)
    MODEL.to(DEVICE)
    MODEL.eval()
    logging.info(f"✅ CLIP model initialized successfully on device: {DEVICE}")
except Exception as e:
    # Handle Model loading failure: Critical, must stop.
    logging.critical(f"❌ Error initializing CLIP model: {e}", exc_info=True)
    raise RuntimeError("Failed to load the CLIP model and processor.") from e

FASHION_CATEGORIES = ['top', 'bottom', 'dresses', 'outerwear', 'swimwear', 'shoes', 'accessories']

def outfit_recommendation_handler(user_prompt: str, budget: float, user_id_key: int | None, image_data: Optional[str] = None, partial_input: Optional[str] = "") -> Dict[str, Any]:
    
    #CRITICAL: IMAGE_DATA NEEDS TO BE ALREADY ENCODED IN base64 BY THE FRONTEND
    #BEFORE GETTING PASSED TO THIS METHOD
    
    partial_list = None
    
    # IN THE FINAL VERSION NOT NEEDED SINCE GEMINI NEEDS TO HANDLE EVERYTHING
    if partial_input:
        requested_categories = [cat.strip() for cat in partial_input.split(',') if cat.strip()]
        valid_categories = [cat for cat in requested_categories]
        partial_list = valid_categories

    if user_id_key:
        user_preferences, gender = get_user_preferences(SUPABASE_CLIENT, user_id_key)
    else:
        user_preferences = None
    user_constraints = get_user_constraints()

    # 1. USER'S QUERY HANDLING
    outfit_json = generate_outfit_plan(GEMINI_CLIENT, GEMINI_MODEL_NAME, user_prompt, image_data, user_preferences, gender, partial_list)
    parsed_item_list = parse_outfit_plan(outfit_json, user_constraints)
    
    #USER'S QUERY IS NOW RE-INTERPRETED TO BETTER UNDERSTAND USER'S INTENT AND WELL FORMATTED IN A JSON STRING
    #CHECK USER'S QUERY FOR HATE-SPEECH OR NOT CONFORMING TO OUTFIT REQUESTS
    if parsed_item_list is None:
        print("Something went wrong with the processing of your request, try again.")
        return {"error": "Something went wrong with the processing of your request, try again.", "status_code": 500}
    
    elif parsed_item_list and 'message' in parsed_item_list[0]:
        return {"message": parsed_item_list[0]['message'], "status_code": 406} #NOT SURE IF STATUS CODE IS CORRECT
        
    # 2. EXTENDED QUERY EMBEDDING
    for item in parsed_item_list:
        query_vector = get_text_embedding_vector(MODEL, PROC, DEVICE, item['description']) #GEMINI EXTENDED QUERY EMBEDDING
        query_vector = query_vector.flatten().tolist() # Convert to list for Supabase (JSON standard)
        item['embedding'] = query_vector

    # 3. CLOTHING ITEMS RETRIEVAL
    all_candidates = search_product_candidates_with_vector_db(SUPABASE_CLIENT, parsed_item_list, budget, gender)
    if 'error' in all_candidates[0]:
        error_detail = all_candidates[0]['error']
        # Return a structured error response
        return {
        "error": "Retrieval Failed: Could not find matching products in the database.",
        "detail": error_detail,
        "status_code": 500 
        }

    # --- UPDATED: Unpack the four return values from the new get_outfit ---
    feasible_outfit: List[Dict[str, Any]]
    remaining_budget: float
    best_full_outfit: List[Dict[str, Any]]
    best_full_cost: float
    
    # 4. OUTFIT ASSEMBLY
    (feasible_outfit, remaining_budget, best_full_outfit, best_full_cost) = get_outfit(all_candidates, budget)
    
    #NEED TO GIVE THE USER THE OPTION TO STILL GET THE FULL OUTFIT EVEN IF OVER BUDGET
    final_result = select_final_outfit_and_metrics(all_candidates, budget, feasible_outfit, remaining_budget, best_full_outfit, best_full_cost)
    
    # If the selection logic returns an error (e.g., Case 3 failure)
    if 'error' in final_result:
        return final_result # Return the error dictionary immediately


    # 5. EXPLANATIONS GENERATION, RIGHT NOW MANDATORY, NEEDS TO BE MADE OPTIONAL
    # ONLY IF THE USER WANTS THEM 
    explanations = explain_selected_outfit(GEMINI_CLIENT, GEMINI_MODEL_NAME, user_prompt, final_result['outfit'])
    final_result['explanation'] = explanations

    # Final successful return
    return final_result 

# --- Web Server Integration (Conceptual) ---
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/outfit', methods=['POST'])
def handle_outfit_request():
    # 1. Get data from the web request body
    data = request.json
    
    # 2. Call the refactored function
    try:
        result = outfit_recommendation_handler(
            user_prompt=data.get('user_prompt'),
            budget=float(data.get('budget')),
            user_id_key=int(data.get('user_id')),
            image_path=data.get('image_path'), # If you handle image uploads
            partial_input=data.get('partial_input')
        )
        return jsonify(result), 200
        
    except Exception as e:
        # Proper error handling
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)