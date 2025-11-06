# src/ai/outfit_retrieval_logic.py (Complete updated file)

import numpy as np
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image 
import webbrowser 
import time # Ensure this is imported at the top

# Import custom modules
from src.data import supabase_queries as supa 
from src.ai.query_embedder import get_text_embedding_vector 
from src.ai import query_handler

# Define global variables for the final time report
total_embed_time = 0
total_sim_time = 0
total_supabase_time = 0 # This will now be set to the time of the single batch query

def search_best_product_with_vector_db(supabase_client, item_category: str, item_desc: str) -> dict | None:
    """
    Finds the single best product match using an indexed vector search in Supabase.
    """
    global total_embed_time, total_supabase_vector_search_time
    
    # 1. TIME QUERY EMBEDDING
    start_embed = time.time()
    query_vector = get_text_embedding_vector(item_desc) #GEMINI EXTENDED QUERY EMBEDDING
    query_vector_list = query_vector.flatten().tolist() # Convert to list for Supabase (JSON standard)
    total_embed_time += (time.time() - start_embed)
    
    # 2. TIME AND EXECUTE VECTOR SEARCH (The database handles the filtering and ranking)
    start_supabase_search = time.time()
    
    df_result = supa.vector_search_rpc_single(
        supabase_client, 
        query_vector_list,
        item_category,  
        #"product_data", 
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


def process_outfit_plan(parsed_item_list: list[dict]) -> list[dict]:
    """
    Orchestrates the retrieval for every item in the LLM's plan using the optimized 
    single-item vector search in a loop.
    """
    # Reset global timers for each top-level call
    global total_embed_time, total_supabase_vector_search_time
    total_embed_time = 0
    total_supabase_vector_search_time = 0
    
    try:
        supabase_client = supa.setup_supabase_client()
    except ValueError as e:
        return [{'error': str(e)}]
        
    if parsed_item_list and 'message' in parsed_item_list[0]:
        return parsed_item_list 

    final_outfit_results = []
    
    for item in parsed_item_list:
        # The key logic is now encapsulated and timed inside this call
        best_match = search_best_product_with_vector_db(
            supabase_client, 
            item_category=item['category'], 
            item_desc=item['description']
        )
        
        result = {'requested_item': item['description'], 'category': item['category']}
        
        if best_match:
            result.update({
                'title': best_match.get('title'), 
                'url': best_match.get('url'),
                'id': best_match.get('id'), 
                'similarity': best_match.get('similarity'),
                'image_link': best_match.get('image_link')
            })
        else:
            result['status'] = 'Product not found in catalog for this category.'
            
        final_outfit_results.append(result)
            
    return final_outfit_results


if __name__ == '__main__':
    # LLM calls, guardrail checks
    user_prompt = input("Enter your outfit request (e.g., 'A comfortable outfit for a remote work day'):\n> ")
    print("\n--- Sending request to Gemini... ---")
    
    start_time_llm = time.time()
    outfit_json = query_handler.generate_outfit_plan(user_prompt)
    parsed_item_list = query_handler.parse_outfit_plan(outfit_json)
    #print(parsed_item_list) #UNCOMMENT TO CHECK WHAT GEMINI COOKED
    end_time_llm = time.time()
    
    if parsed_item_list and 'ERROR' in parsed_item_list[0]:
        # ... (print guardrail ERROR)
        print("\n--- GUARDRAIL MESSAGE ---")
        print(parsed_item_list[0]['ERROR'])
    
    else:
        start_time_retrieval = time.time()
        
        print(f"--- Retrieving {len(parsed_item_list)} matching products... ---")
        
        final_results = process_outfit_plan(parsed_item_list)
        
        end_time_retrieval = time.time()

        # ... (Print JSON Results)
        print("\n--- Final Outfit Retrieval Results (JSON Data) ---")
        if final_results and 'error' in final_results[0]:
            print(f"ERROR: {final_results[0]['error']}")
        else:
            print(json.dumps(final_results, indent=2))
        print("\n" + "="*50)
        
        # ... (5. Terminal Visualization Block)
        start_time_viz = time.time()
        for item in final_results:
            if item.get('image_link'):
                image_url = item['image_link']
                print(f"Match found for {item['requested_item']}:")
                print(f"  Title: {item.get('title')}")
                print(f"  Image URL: {image_url}")
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
        print(f"2. Product Retrieval & Embed:   {end_time_retrieval - start_time_retrieval:.2f} seconds")
        print(f"3. Visualization (Browser Open): {end_time_viz - start_time_viz:.2f} seconds")
        print("-" * 38)
        print("--- RETRIEVAL BREAKDOWN ---")
        print(f"   a. Total Query Embedding:    {total_embed_time:.2f} seconds")
        print(f"   b. Total Supabase Query (BATCH): {total_supabase_time:.2f} seconds")
        print(f"   c. Total Cosine Similarity:  {total_sim_time:.2f} seconds")
        
        # The remaining time is now due to DataFrame copying and filtering (fast)
        retrieval_sum = total_embed_time + total_supabase_time + total_sim_time
        other_retrieval_time = (end_time_retrieval - start_time_retrieval) - retrieval_sum
        print(f"   d. Other Retrieval Ops (Filtering, Pandas): {other_retrieval_time:.2f} seconds")

        print("-" * 50)
        print(f"TOTAL RUNTIME:               {time.time() - start_time_llm:.2f} seconds")
        print("="*50)