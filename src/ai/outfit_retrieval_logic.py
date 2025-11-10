# src/ai/outfit_retrieval_logic.py (Complete updated file)

import numpy as np
import pandas as pd
from typing import List
from supabase import Client

def vector_search_rpc_candidates(client: Client, query_vector: np.ndarray, category: str, budget: float, gender: str, limit: int = 10, threshold: float = 0.0) -> pd.DataFrame:
    """
    Calls the optimized PostgreSQL RPC function (search_outfits) to find the best match 
    for a single query vector within a specified category.
    
    This function is necessary because PostgREST does not support the pgvector similarity operator.
    """
    try:
        
        # Call the RPC function defined in PostgreSQL
        response = client.rpc(
            "search_outfits",
            {
                "query_embedding": query_vector,
                "match_threshold": threshold,
                "match_count": limit,
                "category_in": category, # The main_category filter
                "max_espense": budget,
                "gender": gender
            }
        ).execute()

        if not response.data:
            return pd.DataFrame()
            
        # The result already includes the calculated 'similarity' score
        df = pd.DataFrame(response.data)
        
        return df

    except Exception as e:
        print(f"Supabase RPC search error for category '{category}': {e}")
        return pd.DataFrame()

def search_product_candidates_with_vector_db(client, parsed_item_list, budget, gender) -> List[List[dict]] | List[dict]:
    """
    Finds the single best product match using an indexed vector search in Supabase.
    """
    all_candidates = []

    # 2. TIME AND EXECUTE VECTOR SEARCH (The database handles the filtering and ranking)

    for item in parsed_item_list:
    # print("DEBUG: ", item['embedding'])
        df_candidates = vector_search_rpc_candidates(
            client, 
            item['embedding'],
            item['category'],
            budget, 
            gender
        )

        if not df_candidates.empty:
            candidate_list = df_candidates.to_dict('records')
            all_candidates.append(candidate_list)
        else:
            print(f"Warning: No candidates found for {item['description']} ({item['category']}). Cannot form a full outfit.")
            return [{"error": f"Failed to find candidates for {item['category']}. Cannot proceed with Knapsack optimization."}]
                    
    # Return the entire DataFrame of candidates
    return all_candidates
