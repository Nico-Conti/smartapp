import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional
import json
import numpy as np


# Load environment variables once for the module
load_dotenv()

# --- Global Initialization ---
# The client object is NOT initialized globally here because it needs to be 
# instantiated correctly when the request is processed, but we define the access
# methods. The keys are retrieved from the environment variables.
SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.environ.get("SUPABASE_KEY")

# --- Core Functions ---

def setup_supabase_client() -> Client:
    """
    Initializes and returns the Supabase client object.
    
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY environment variables are missing.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials (SUPABASE_URL, SUPABASE_KEY) must be set in the environment or .env file.")
        
    try:
        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        # In a real app, you'd handle this more gracefully (e.g., logging and returning a 500 error)
        raise
    

def vector_search_rpc_single(client: Client, query_vector: np.ndarray, category: str, max_espense: float, limit: int = 1, threshold: float = 0.0) -> pd.DataFrame:
    """
    Calls the optimized PostgreSQL RPC function (search_outfits) to find the best match 
    for a single query vector within a specified category.
    
    This function is necessary because PostgREST does not support the pgvector similarity operator.
    """
    try:
        # The RPC function expects a list of floats for the embedding
        #embedding_list = query_vector.tolist()
        
        # Call the RPC function defined in PostgreSQL
        response = client.rpc(
            "search_outfits",
            {
                "query_embedding": query_vector,
                "match_threshold": threshold,
                "match_count": limit,
                "category_in": category, # The main_category filter
                "max_espense": max_espense
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
    

def get_user_preferences(client: Client, user_id_key: int) -> dict | None:
    """
    Retrieves a user's preferences (favorite_color, favorite_material, favorite_brand) 
    from the users_prova_preferences table using the unique user ID (UID).

    Args:
        client: The initialized Supabase Client instance.
        user_id_key: The unique User ID (UID) obtained from Supabase Auth.

    Returns:
        A dictionary containing the preferences (e.g., {'favorite_color': 'blue', ...})
        or None if no preferences are found or an error occurs.
    """
    
    # 1. Define the specific columns to select
    select_columns = "favorite_color, favorite_material, favorite_brand"
    
    try:
        # 2. Query the table, filter by the user's UID, and limit to 1 result
        response = client.table('users_prova_preferences').select(select_columns).eq(
            'user_id', # Column in your table that stores the user's UID (Ensure this column name is correct)
            user_id_key
        ).limit(1).execute() 

        # 3. Check if data was returned
        if not response.data:
            #print(f"No preferences found for user ID: {user_id_key}")
            return None
        
        # 4. Return the single result dictionary
        # response.data is a list of dictionaries, so we take the first element [0]
        return response.data[0]
        
    except Exception as e:
        print(f"Error retrieving user preferences for {user_id_key}: {e}")
        return None

#ONLY USED FOR LOCAL AND TARGETED TESTING
def query_products_in_main_category(client: Client, category: str, table_name: str) -> pd.DataFrame:
    """
    Fetches all products for a given main category from the specified table.
    
    Args:
        client: The initialized Supabase client.
        category: The main clothing category (e.g., 'top', 'bottom').
        table_name: The name of the table containing the product data.
        
    Returns:
        A pandas DataFrame containing the product data, including the embeddings.
    """
    # NOTE: Your original notebook used 'dresses' logic separately, 
    # but the simplest approach is to fetch all products that match the main category.
    # The categories in the database must match the keys from the LLM output (top, bottom, dresses, etc.)
    
    try:
        # 1. Query the Supabase table
        response = client.table(table_name).select("*").eq("main_category", category).execute()

        # 2. Check for data and errors
        if not response.data:
            print(f"No data found for category: {category}")
            return pd.DataFrame()
            
        # 3. Convert the list of dictionaries (records) into a DataFrame
        df = pd.DataFrame(response.data)
        return df

    except Exception as e:
        print(f"Supabase query error for category '{category}': {e}")
        return pd.DataFrame()

#####AS OF NOW NOT USED SINCE THE VECTOR SEARCH IS MUCH MORE EFFICIENT
# def query_products_in_multiple_categories(client: Client, categories: list[str], table_name: str) -> pd.DataFrame:
#     """
#     Fetches all products for a list of main categories from the specified table using a single query.
    
#     Args:
#         client: The initialized Supabase client.
#         categories: A list of main clothing categories (e.g., ['top', 'bottom', 'shoes']).
#         table_name: The name of the table containing the product data.
        
#     Returns:
#         A pandas DataFrame containing all product data for the requested categories.
#     """
#     if not categories:
#         return pd.DataFrame()
        
#     try:
#         # 1. Query the Supabase table using the .in_() method
#         response = client.table(table_name)\
#                          .select("*")\
#                          .in_("main_category", categories)\
#                          .execute()

#         # 2. Check for data and errors
#         if not response.data:
#             print(f"No data found for categories: {categories}")
#             return pd.DataFrame()
            
#         # 3. Convert the list of dictionaries (records) into a DataFrame
#         df = pd.DataFrame(response.data)
#         return df

#     except Exception as e:
#         print(f"Supabase batch query error for categories '{categories}': {e}")
#         return pd.DataFrame()

#ONLY USED FOR LOCAL AND TARGETED TESTING
if __name__ == '__main__':
    try:
        print("Testing Supabase connection and query...")
        
        # 1. Setup client
        supabase_client = setup_supabase_client()
        print("Supabase client initialized successfully.")
        
        # 2. Test query for a category
        test_category = "top" # Example category, adjust as needed
        df = query_products_in_main_category(supabase_client, test_category, "product_data")
        
        if not df.empty:
            print(f"\nSuccessfully fetched {len(df)} products for '{test_category}'.")
            print("First 5 rows and columns:")
            print(df.head())
            
            # Verify the crucial 'img_embedding' column exists
            if 'img_embedding' in df.columns:
                print("\n'img_embedding' column confirmed.")
            else:
                print("\nCRITICAL WARNING: 'img_embedding' column NOT found. Check your database schema.")
        else:
            print(f"\nTest failed: Did not fetch any products for '{test_category}'.")
            
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")