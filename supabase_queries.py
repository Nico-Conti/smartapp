import os
import json
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

def setup_supabase_client() -> Client:
    """
    Initializes and returns the Supabase client instance using the provided URL and key.

    Args:
        url: The Supabase project URL.
        key: The Supabase secret or anonymous key.

    Returns:
        The initialized Supabase Client object.
    """
    try:
        load_dotenv() 
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY") 

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

        print(f"✅ Supabase client successfully initialized.")

        return supabase
    
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client. Error: {e}")
        # Return None or raise the error for the calling script to handle
        return None 



def check_if_value_exists_in_colum(supabase_client: Client, table_name: str, column_name: str, value: str) -> bool:
    

    try:
        # print(f"Starting single match existence check on '{table_name}' for {column_name} = '{value}'...")
        
        # 1. Select only the column we're filtering on (minimal payload)
        # 2. Filter for the matching value
        # 3. Limit to 1 (stop searching after first match)
        # 4. Use maybe_single() to handle 0 or 1 result gracefully
        response = (
            supabase_client.table(table_name)
            .select(column_name)  
            .eq(column_name, value)
            .limit(1)  
            .maybe_single()
            .execute()
        )
        
        
        # response.data will be a dictionary (the matching record) or None (no match).
        exists = response.data is not None
        

        return exists
            
    except Exception as e:
        # print(f"❌ Error during existence check: {e}")
        return False
            


def query_products_in_main_category(supabase_client: Client, main_category: str, table_name: str) -> pd.DataFrame:

    print(f"Querying records in main category: '{main_category}'...")
    
    response = (
        supabase_client.table(table_name)
        .select("*")  # Select all columns
        .eq("main_category", main_category)  # Filter by main category
        .execute()
    )
    
    # Convert the response data to a pandas DataFrame
    data = response.data
    df = pd.DataFrame(data)
    
    print(f"✅ Retrieved {len(df)} records in main category '{main_category}'.")

    
    return df

def query_products_in_role(supabase_client: Client, role: str, table_name: str) -> pd.DataFrame:

    print(f"Querying records in role: '{role}'...")

    response = (
        supabase_client.table(table_name)
        .select("*")  # Select all columns
        .eq("role", role)  # Filter by main category
        .execute()
    )

    # Convert the response data to a pandas DataFrame
    data = response.data
    df = pd.DataFrame(data)

    print(f"✅ Retrieved {len(df)} records in main category '{role}'.")


    return df

def load_table(supabase_client: Client, table_name: str):

    response = (
        supabase_client.table(table_name)
        .select("*")  # Select all columns
        .limit(1000000)  # Limit to 1,000,000 records
        .execute()
    )
    data = response.data
    df = pd.DataFrame(data)
    print(f"✅ Loaded {len(df)} records from table '{table_name}'.")