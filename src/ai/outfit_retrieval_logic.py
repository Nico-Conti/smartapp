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


def search_product_candidates_with_vector_db(item, budget) -> dict | None:
    """
    Finds the single best product match using an indexed vector search in Supabase.
    """
    global total_supabase_vector_search_time
    
    # 2. TIME AND EXECUTE VECTOR SEARCH (The database handles the filtering and ranking)
    start_supabase_search = time.time()
    # print("DEBUG: ", item['embedding'])
    df_candidates = supa.vector_search_rpc_candidates(
        SUPABASE_CLIENT, 
        item['embedding'],
        item['category'],
        budget
    )
    total_supabase_vector_search_time += (time.time() - start_supabase_search)
            
    if df_candidates.empty:
        return pd.DataFrame()
        
    # Return the entire DataFrame of candidates
    return df_candidates


def run_knapsack_solver(processed_candidates, budget: float):
    """
    Implements the Dynamic Programming solution for the Multi-Choice Knapsack Problem.
    Finds the best combination (max similarity) of one item per category within budget.
    """
    num_categories = len(processed_candidates)
    max_budget_cents = int(round(budget * 100))

    # dp_similarity[w]: Max total similarity achievable with a total cost of 'w' cents.
    dp_similarity = np.full(max_budget_cents + 1, -1.0)
    dp_similarity[0] = 0.0 

    # path_table[i][w] stores the INDEX (within its candidate list) of the item 
    # selected from CATEGORY i-1 that resulted in a total cost of 'w' cents.
    path_table = np.full((num_categories + 1, max_budget_cents + 1), -1, dtype=int) 

    # 1. Dynamic Programming Iteration
    for i, category_items in enumerate(processed_candidates):
        # We need a fresh copy to prevent using items from the current category multiple times
        new_dp_similarity = np.copy(dp_similarity)
        
        for current_cost_cents in range(max_budget_cents + 1):
            # Only proceed if the previous state (before this category) was reachable
            if dp_similarity[current_cost_cents] >= 0:
                
                # Try adding an item from the current category (i)
                for item_idx, item in enumerate(category_items):
                    item_cost_cents = item['price_in_cents']
                    new_cost_cents = current_cost_cents + item_cost_cents
                    
                    if new_cost_cents <= max_budget_cents:
                        new_total_similarity = dp_similarity[current_cost_cents] + item['similarity']
                        
                        # Check if this new combination is better than the existing one for new_cost_cents
                        if new_total_similarity > new_dp_similarity[new_cost_cents]:
                            new_dp_similarity[new_cost_cents] = new_total_similarity
                            
                            # Record the index of the item selected from the current category (i)
                            # The path is traced backward: path_table[i+1][new_cost_cents] stores the 
                            # item index from category 'i' chosen to reach this state.
                            path_table[i+1][new_cost_cents] = item_idx
                            
        # Update DP array for the next iteration (next category)
        dp_similarity = new_dp_similarity

    # 2. Find the Optimal Result (Max Similarity within Budget)
    best_similarity = -1.0
    best_cost_cents = -1

    # Search for the highest similarity across all valid costs
    for cost in range(max_budget_cents, -1, -1):
        if dp_similarity[cost] > best_similarity:
            best_similarity = dp_similarity[cost]
            best_cost_cents = cost

    # 3. Traceback to reconstruct the outfit
    final_outfit_results = []
    if best_cost_cents > 0 and best_similarity > 0:
        current_cost_cents = best_cost_cents
        
        # Iterate backwards through the categories
        for i in range(num_categories - 1, -1, -1):
            # Item index from category 'i' is stored in path_table[i+1]
            item_index = path_table[i+1][current_cost_cents]
            
            if item_index == -1:
                 # Safety break: should not happen if DP logic is sound
                 return [], 0.0
            
            # Retrieve the selected item data
            selected_item = processed_candidates[i][item_index]
            final_outfit_results.append(selected_item['data'])
            
            # Update the cost to the state *before* this item was added
            item_cost_cents = selected_item['price_in_cents']
            current_cost_cents -= item_cost_cents
            
        # Results collected backwards, reverse them to match original category order
        final_outfit_results.reverse()
        
        # Calculate the actual total price
        total_price = best_cost_cents / 100
        return final_outfit_results, total_price
        
    return [], 0.0 # Failed to find a valid combination


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
    all_candidates = []

    for i, item in enumerate(parsed_item_list):
        # The key logic is now encapsulated and timed inside this call
        df_candidates = search_product_candidates_with_vector_db(item, budget)

        if not df_candidates.empty:
            candidate_list = df_candidates.to_dict('records')
            all_candidates.append(candidate_list)
        else:
            print(f"Warning: No candidates found for {item['description']} ({item['category']}). Cannot form a full outfit.")
            return [{"error": f"Failed to find candidates for {item['category']}. Cannot proceed with Knapsack optimization."}], budget
        
        result = {'requested_item': item['description'], 'category': item['category']}
    
    if not all_candidates or len(all_candidates) != len(parsed_item_list):
        return [{"error": "Incomplete candidate list. Cannot proceed."}], budget
        
    processed_candidates = []
    for category_list in all_candidates:
        category_items = []
        for item in category_list:
            category_items.append({
                'price_in_cents': int(round(item['price'] * 100)),
                'similarity': item['similarity'],
                'data': item # Keep a reference to the original data
            })
        processed_candidates.append(category_items)


    # 3. Run the Knapsack Solver
    final_outfit_results, total_price_selected = run_knapsack_solver(processed_candidates, budget)

    # 4. Final Formatting and Budget Calculation
    if final_outfit_results:
        remaining_budget = budget - total_price_selected

        formatted_results = []
        for i, item_match in enumerate(final_outfit_results):
            original_item = parsed_item_list[i]
            formatted_results.append({
                'requested_item': original_item['description'],
                'category': original_item['category'],
                'title': item_match.get('title'),
                'url': item_match.get('url'),
                'id': item_match.get('id'),
                'similarity': float(f"{item_match.get('similarity'):.4f}"),
                'image_link': item_match.get('image_link'),
                'price': item_match.get('price')
            })
            
        return formatted_results, remaining_budget
    
    # Knapsack solver failed to find a valid combination within budget
    return [{"error": f"Knapsack solver failed to find a combination under the budget of €{budget:.2f}."}], budget


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