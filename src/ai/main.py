import os
import webbrowser 
import time
import json
from google import genai
from supabase import create_client, Client
from google.genai import Client
from transformers import CLIPProcessor, CLIPModel
from typing import Optional
from dotenv import load_dotenv

# Import custom modules
from src.ai.get_user_preferences import get_user_preferences
from src.ai.query_handler import generate_outfit_plan, parse_outfit_plan
from src.ai.query_embedder import get_text_embedding_vector 
from src.ai.outfit_retrieval_logic import search_product_candidates_with_vector_db
from src.ai.assemble_outfit import get_outfit
from src.ai.get_explanations import explain_selected_outfit

# --- 1. Global Initialization (Loaded only ONCE when the server starts) ---

# Load environment variables (like the GEMINI_API_KEY)
load_dotenv()

SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials (SUPABASE_URL, SUPABASE_KEY) must be set in the environment or .env file.")
    
try:
    SUPABASE_CLIENT: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    # In a real app, you'd handle this more gracefully (e.g., logging and returning a 500 error)
    raise

# Initialize the Gemini Client ONCE
# This client object will be reused for every API call.
GEMINI_CLIENT = genai.Client()

MODEL_NAME = 'gemini-2.0-flash'

# --- Global Initialization (Loaded only ONCE) ---
MODEL_NAME = "patrickjohncyh/fashion-clip"
MODEL = CLIPModel.from_pretrained(MODEL_NAME)
PROC = CLIPProcessor.from_pretrained(MODEL_NAME, use_fast=True)
DEVICE = "cpu" # Use 'cuda' if GPU is available
MODEL.to(DEVICE)
MODEL.eval()

if __name__ == '__main__':
    while True:
        user_prompt = input("Enter your outfit request (e.g., 'A comfortable outfit for a remote work day'):\n> ")
        budget = float(input("Enter the max budget(€) for the whole outfit:\n"))

        user_id_key = int(input("Enter your Supabase Auth User ID (UID) for preference lookup:\n> "))
        user_preferences, gender = get_user_preferences(SUPABASE_CLIENT, user_id_key)

        print("\n--- Sending request to Gemini... ---")

        # 1. USER'S QUERY HANDLING
        start_time_llm = time.time()
        outfit_json = generate_outfit_plan(GEMINI_CLIENT, MODEL_NAME, user_prompt, user_preferences)
        parsed_item_list = parse_outfit_plan(outfit_json)
        print(parsed_item_list) #UNCOMMENT TO CHECK WHAT GEMINI COOKED
        end_time_llm = time.time()
        
        #USER'S QUERY IS NOW RE-INTERPRETED TO BETTER UNDERSTAND USER'S INTENT AND WELL FORMATTED IN A JSON STRING
        #CHECK USER'S QUERY FOR HATE-SPEECH OR NOT CONFORMING TO OUTFIT REQUESTS
        if parsed_item_list is None:
            print("Something went wrong with the processing of your request, try again.")
            continue
        
        elif parsed_item_list and 'message' in parsed_item_list[0]:
            # ... (print guardrail message)
            print("\n--- GUARDRAIL MESSAGE ---")
            print(parsed_item_list[0]['message'])
            continue
            
        # 2. EXTENDED QUERY EMBEDDING
        start_time_embed = time.time()
        for item in parsed_item_list:
            query_vector = get_text_embedding_vector(MODEL, PROC, DEVICE, item['description']) #GEMINI EXTENDED QUERY EMBEDDING
            query_vector = query_vector.flatten().tolist() # Convert to list for Supabase (JSON standard)
            item['embedding'] = query_vector
        end_time_embed = time.time()

        # 3. CLOTHING ITEMS RETRIEVAL
        print(f"--- Retrieving {len(parsed_item_list)} matching products... ---")
        start_time_retrieval = time.time()
        
        all_candidates = search_product_candidates_with_vector_db(SUPABASE_CLIENT, parsed_item_list, budget, gender)
        if 'error' in all_candidates[0]:
            print(all_candidates[0])
            continue

        end_time_retrieval = time.time()

        # 4. FINAL OUTFIT ASSEMBLY
        start_time_assembly = time.time()

        final_outfit_results, remaining_budget = get_outfit(all_candidates, budget)
        is_error = not final_outfit_results or ('error' in final_outfit_results[0])
        
        if is_error:
            # We already know it's either empty or contains an error dict.
            if final_outfit_results:
                 print(final_outfit_results[0])
            else:
                 print({"error": "Outfit assembly returned an unexpected empty result list."})
            continue

        end_time_assembly = time.time()

        start_time_explanations = time.time()
        explanations = explain_selected_outfit(GEMINI_CLIENT, MODEL_NAME, user_prompt, final_outfit_results)
        end_time_explanations = time.time()
        print("Explanations for the retrieved outfit:\n", explanations)

        # ... (Print JSON Results)
        print("\n--- Final Outfit Retrieval Results (JSON Data) ---")
        if final_outfit_results and 'error' in final_outfit_results[0]:
            print(f"ERROR: {final_outfit_results[0]['error']}")
        else:
            print(json.dumps(final_outfit_results, indent=2))
            print("FINAL REMAINING BUDGET, HOPING IT IS >= 0:", remaining_budget)
        print("\n" + "="*50)
        
        # ... (5. Terminal Visualization Block)
        start_time_viz = time.time()
        for item in final_outfit_results:
            if item.get('image_link'):
                image_url = item['image_link']
                url = item['url']
                print(f"  Title: {item.get('title')}")
                print(f"  Image URL: {image_url}")
                print(f"  URL for Purchase: {url}")
                try:
                    webbrowser.open_new_tab(image_url)
                    print("  --> Image opened in your default web browser.")
                except Exception as e:
                    print(f"  Could not automatically open browser: {e}")
            
            elif item.get('status'):
                print(f"No match found for {item['requested_item']}: {item['status']}\n")
        end_time_viz = time.time()
        
        # --- FINAL TIME REPORT ---
        print("\n" + "="*50)
        print("--- EXECUTION TIME BREAKDOWN (Total) ---")
        print(f"1. LLM Generation & Parsing:   {end_time_llm - start_time_llm:.2f} seconds")
        print(f"2. Items embeddings: {end_time_embed - start_time_embed:.6f} seconds")
        print(f"3. Product Retrieval:   {end_time_retrieval - start_time_retrieval:.2f} seconds")
        print(f"3. Outfit assembly:   {end_time_assembly - start_time_assembly:.2f} seconds")
        print(f"4. Explanations:   {end_time_explanations - start_time_explanations:.2f} seconds")
        print(f"5. Visualization (Browser Open): {end_time_viz - start_time_viz:.2f} seconds")

        print("-" * 50)
        print(f"TOTAL RUNTIME:               {time.time() - start_time_llm:.2f} seconds")
        print("="*50)