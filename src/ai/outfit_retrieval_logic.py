# src/ai/outfit_retrieval_logic.py (Complete updated file)

import numpy as np
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image 
import webbrowser 
import time # Ensure this is imported at the top
import sys 

# Import custom modules
from src.data import supabase_queries as supa 
from src.ai.query_embedder import get_text_embedding_vector 
from src.ai import query_handler

try:
    # This will execute as soon as the module is imported
    SUPABASE_CLIENT = supa.setup_supabase_client()
except ValueError as e:
    print(f"FATAL: Supabase client failed to initialize: {e}")
    sys.exit(1)


def search_best_product_with_vector_db(item, max_espense) -> dict | None:
    """
    Finds the single best product match using an indexed vector search in Supabase.
    """
    global total_supabase_vector_search_time
    
    # 2. TIME AND EXECUTE VECTOR SEARCH (The database handles the filtering and ranking)
    start_supabase_search = time.time()
    # print("DEBUG: ", item['embedding'])
    df_result = supa.vector_search_rpc_single(
        SUPABASE_CLIENT, 
        item['embedding'],
        item['category'],  
        max_espense, 
        limit=1
    )
    total_supabase_vector_search_time += (time.time() - start_supabase_search)
    
    if df_result.empty:
        return None
        
    best_match = df_result.iloc[0].to_dict()
    print(best_match)
    
    # The DB returns 'similarity' sincee the <=> operator calculates distance and we return similarity as i - (query_embedding - img_embedding).
    similarity = best_match.pop('similarity')
    best_match['similarity'] = float(f"{similarity:.4f}") 
    
    return best_match


def process_outfit_plan(parsed_item_list: list[dict], budget: float) -> list[dict]:
    """
    Orchestrates the retrieval for every item in the LLM's plan using the optimized 
    single-item vector search in a loop.
    """
    # Reset global timers for each top-level call
    global total_embed_time, total_supabase_vector_search_time
    total_embed_time = 0
    total_supabase_vector_search_time = 0

    remaining_budget = budget
    
    if parsed_item_list and 'message' in parsed_item_list[0]:
        return parsed_item_list 

    final_outfit_results = []
    
    for i, item in enumerate(parsed_item_list):
        # The key logic is now encapsulated and timed inside this call
        max_espence = (budget / len(parsed_item_list)) if i != (len(parsed_item_list) - 1) else remaining_budget
        best_match = search_best_product_with_vector_db(item, max_espence)
        remaining_budget -= best_match.get('price')
        
        result = {'requested_item': item['description'], 'category': item['category']}
        
        if best_match:
            result.update({
                'title': best_match.get('title'), 
                'url': best_match.get('url'),
                'id': best_match.get('id'), 
                'similarity': best_match.get('similarity'),
                'image_link': best_match.get('image_link'), 
                'price': best_match.get('price')
            })
        else:
            result['status'] = 'Product not found in catalog for this category.'
            
        final_outfit_results.append(result)
            
    return final_outfit_results, remaining_budget


if __name__ == '__main__':
    # LLM calls, guardrail checks
    user_prompt = input("Enter your outfit request (e.g., 'A comfortable outfit for a remote work day'):\n> ")
    budget = float(input("Enter the max budget(€) for the whole outfit:\n"))

    user_id_key = int(input("Enter your Supabase Auth User ID (UID) for preference lookup:\n> "))
    user_preferences = supa.get_user_preferences(SUPABASE_CLIENT, user_id_key)

    print("\n--- Sending request to Gemini... ---")
    
    start_time_llm = time.time()
    outfit_json = query_handler.generate_outfit_plan(user_prompt, user_preferences)
    parsed_item_list = query_handler.parse_outfit_plan(outfit_json)
    #print(parsed_item_list) #UNCOMMENT TO CHECK WHAT GEMINI COOKED
    end_time_llm = time.time()
    #USER'S QUERY IS NOW RE-INTERPRETED TO BETTER UNDERSTAND USER'S INTENT AND WELL FORMATTED IN A JSON STRING

    #CHECK USER'S QUERY FOR HATE-SPEECH OR NOT CONFORMING TO OUTFIT REQUESTS
    if parsed_item_list and 'ERROR' in parsed_item_list[0]:
        # ... (print guardrail ERROR)
        print("\n--- GUARDRAIL MESSAGE ---")
        print(parsed_item_list[0]['ERROR'])
    
    else:
        
        # 1. EXTENDED QUERY EMBEDDING
        start_time_embed = time.time()
        for item in parsed_item_list:
            query_vector = get_text_embedding_vector(item['description']) #GEMINI EXTENDED QUERY EMBEDDING
            query_vector = query_vector.flatten().tolist() # Convert to list for Supabase (JSON standard)
            item['embedding'] = query_vector
        end_time_embed = time.time()

        print(f"--- Retrieving {len(parsed_item_list)} matching products... ---")
        
        # 2. OUTFIT RETRIEVAL
        start_time_retrieval = time.time()
        final_results, remaining_budget = process_outfit_plan(parsed_item_list, budget)
        end_time_retrieval = time.time()

        # ... (Print JSON Results)
        print("\n--- Final Outfit Retrieval Results (JSON Data) ---")
        if final_results and 'error' in final_results[0]:
            print(f"ERROR: {final_results[0]['error']}")
        else:
            print(json.dumps(final_results, indent=2))
            print("FINAL REMAINING BUDGET, HOPING IT IS >= 0:", remaining_budget)
        print("\n" + "="*50)
        
        # ... (5. Terminal Visualization Block)
        start_time_viz = time.time()
        for item in final_results:
            if item.get('image_link'):
                image_url = item['image_link']
                url = item['url']
                print(f"Match found for {item['requested_item']}:")
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
        print(f"4. Visualization (Browser Open): {end_time_viz - start_time_viz:.2f} seconds")

        print("-" * 50)
        print(f"TOTAL RUNTIME:               {time.time() - start_time_llm:.2f} seconds")
        print("="*50)