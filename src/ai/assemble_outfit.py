import numpy as np

def get_outfit(all_candidates, budget: float):
    """
    Implements the Dynamic Programming solution for the Multi-Choice Knapsack Problem.
    Finds the best combination (max similarity) of one item per category within budget.
    """

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

        remaining_budget = budget - total_price

        formatted_results = []
        for i, item_match in enumerate(final_outfit_results):
            formatted_results.append({
                'title': item_match.get('title'),
                'url': item_match.get('url'),
                'id': item_match.get('id'),
                'similarity': float(f"{item_match.get('similarity'):.4f}"),
                'image_link': item_match.get('image_link'),
                'price': item_match.get('price')
            })
        
        return formatted_results, remaining_budget
        
    return [{"error": f"Knapsack solver failed to find a combination under the budget of €{budget:.2f}."}], budget # Failed to find a valid combination