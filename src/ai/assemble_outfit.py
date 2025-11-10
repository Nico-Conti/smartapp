import numpy as np
from typing import List, Dict, Tuple

# Helper function for the Knapsack DP logic, designed to be reusable.
def _run_knapsack_dp(
    processed_candidates: List[List[Dict]], 
    max_budget_cents: int, 
    num_categories: int
) -> Tuple[List[Dict], float, int]:
    """
    Core Dynamic Programming logic. Finds the best similarity score and the path 
    to achieve it under the given max_budget_cents.
    
    Note: If 'SKIP' items were added, they will be ignored in the traceback.
    """
    
    # dp_similarity[w]: Max total similarity achievable with a total cost of 'w' cents.
    dp_similarity = np.full(max_budget_cents + 1, -1.0)
    dp_similarity[0] = 0.0 

    # path_table[i][w] stores the INDEX (within its candidate list) of the item 
    # selected from CATEGORY i-1 that resulted in a total cost of 'w' cents.
    path_table = np.full((num_categories + 1, max_budget_cents + 1), -1, dtype=int) 

    # 1. Dynamic Programming Iteration
    current_dp = dp_similarity
    for i, category_items in enumerate(processed_candidates):
        # Use a fresh copy to prevent using items from the current category multiple times
        new_dp_similarity = np.copy(current_dp)
        
        for current_cost_cents in range(max_budget_cents + 1):
            # Only proceed if the previous state (before this category) was reachable
            if current_dp[current_cost_cents] >= 0:
                
                # Try adding an item from the current category (i)
                for item_idx, item in enumerate(category_items):
                    item_cost_cents = item['price_in_cents']
                    new_cost_cents = current_cost_cents + item_cost_cents
                    
                    # Check the budget constraint for this run
                    if new_cost_cents <= max_budget_cents:
                        new_total_similarity = current_dp[current_cost_cents] + item['similarity']
                        
                        # Check if this new combination is better than the existing one for new_cost_cents
                        if new_total_similarity > new_dp_similarity[new_cost_cents]:
                            new_dp_similarity[new_cost_cents] = new_total_similarity
                            # Record the index of the item selected from the current category (i)
                            path_table[i+1][new_cost_cents] = item_idx
                            
        current_dp = new_dp_similarity

    # 2. Find the Optimal Result (Max Similarity)
    best_similarity = -1.0
    best_cost_cents = -1

    # Search for the highest similarity across all valid costs
    for cost in range(max_budget_cents, -1, -1):
        if current_dp[cost] > best_similarity:
            best_similarity = current_dp[cost]
            best_cost_cents = cost

    # 3. Traceback
    final_outfit_results = []
    
    # Ensure a non-empty result was found
    if best_cost_cents >= 0 and best_similarity > 0:
        current_cost_cents = best_cost_cents
        
        # Iterate backwards through the categories
        for i in range(num_categories - 1, -1, -1):
            # Item index from category 'i' is stored in path_table[i+1]
            item_index = path_table[i+1][current_cost_cents]
            
            # The item index must be non-negative to indicate a selection was made
            if item_index >= 0:
                selected_item = processed_candidates[i][item_index]
                
                # We trace back ONLY if the item wasn't the 'SKIP' placeholder
                if selected_item['price_in_cents'] != 0 or selected_item['similarity'] != 0.0:
                    final_outfit_results.append(selected_item['data'])
                    
                    # Update the cost to the state *before* this item was added
                    item_cost_cents = selected_item['price_in_cents']
                    current_cost_cents -= item_cost_cents
                # If it is a SKIP item, current_cost_cents remains the same.
                
        # Results collected backwards, reverse them to match original category order
        final_outfit_results.reverse()
        
    return final_outfit_results, best_similarity, best_cost_cents


def get_outfit(all_candidates: List[List[Dict]], budget: float) -> Tuple[List[Dict], float, List[Dict], float]:
    """
    Implements the Dynamic Programming solution, returning the best feasible (partial/full) 
    outfit and the best infeasible (full) outfit for suggestion.
    
    Returns: (feasible_outfit, feasible_remaining_budget, best_full_outfit, best_full_cost)
    """

    num_categories = len(all_candidates)
    max_budget_cents = int(round(budget * 100))
    
    # Calculate a budget large enough to ensure the DP finds the highest similarity 
    # score for the full outfit, regardless of the user's budget.
    max_total_possible_price = sum(max(item['price'] for item in cat) for cat in all_candidates)
    huge_budget_cents = int(round(max_total_possible_price * 100)) + max_budget_cents + 1000 
    
    
    # --- PRE-PROCESSING CANDIDATES (Original structure) ---
    original_processed_candidates = []
    for category_list in all_candidates:
        category_items = []
        for item in category_list:
            category_items.append({
                'price_in_cents': int(round(item['price'] * 100)),
                'similarity': item['similarity'],
                'data': item # Keep a reference to the original data
            })
        original_processed_candidates.append(category_items)


    # --- SCENARIO 1: BEST FEASIBLE (PARTIAL OR FULL) OUTFIT (Primary Recommendation) ---
    # Allow skipping an item by adding a 0-cost, 0-similarity placeholder.
    feasible_processed_candidates = []
    for category_items in original_processed_candidates:
        # Index 0 is the SKIP option (ensures price and similarity are unique for traceback logic)
        skip_item = {
            'price_in_cents': 0,
            'similarity': 0.0,
            'data': {'title': 'SKIP', 'price': 0.0} 
        }
        feasible_processed_candidates.append([skip_item] + category_items)
        
    feasible_outfit, _, feasible_cost_cents = _run_knapsack_dp(
        feasible_processed_candidates, 
        max_budget_cents, 
        num_categories
    )
    
    feasible_remaining_budget = budget - (feasible_cost_cents / 100)
    
    
    # --- SCENARIO 2: BEST FULL OUTFIT (May be Infeasible/Over Budget) ---
    # 1. Use original candidates (no skips allowed, forcing one item per category)
    # 2. Use a huge budget to ensure the DP finishes finding the max similarity score
    
    best_full_outfit, _, best_full_cost_cents = _run_knapsack_dp(
        original_processed_candidates, 
        huge_budget_cents, # Ignore the true budget limit here
        num_categories
    )
    
    best_full_cost = best_full_cost_cents / 100
    

    # --- FINAL FORMATTING & RETURN ---
    
    def format_results(outfit_list):
        """Formats the list of selected item dicts for final output."""
        formatted_list = []
        for item_match in outfit_list:
            # Recreate the expected output dictionary structure
            formatted_list.append({
                'title': item_match.get('title'),
                'url': item_match.get('url'),
                'id': item_match.get('id'),
                'similarity': float(f"{item_match.get('similarity'):.4f}"),
                'image_link': item_match.get('image_link'),
                'price': item_match.get('price')
            })
        return formatted_list

    formatted_feasible_outfit = format_results(feasible_outfit)
    formatted_best_full_outfit = format_results(best_full_outfit)
    
    # Handle edge case where no feasible items were selected at all.
    if not formatted_feasible_outfit and formatted_best_full_outfit:
        # If the best budget-compliant choice was to skip everything, we still 
        # return the full outfit as the alternative suggestion.
        pass
        
    return (
        formatted_feasible_outfit, 
        feasible_remaining_budget, 
        formatted_best_full_outfit, 
        best_full_cost
    )