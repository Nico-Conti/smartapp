from supabase import Client

def get_user_preferences(client: Client, user_id_key: int) -> dict | None:
    """
    Retrieves a user's preferences (favorite_color, favorite_material, favorite_brand) 
    from the users_prova_preferences table using the unique user ID (UID).
    """
    
    # 1. Define the specific columns to select
    select_columns = "favorite_color, favorite_material, favorite_brand, gender"
    
    try:
        # 2. Query the table, filter by the user's UID, and limit to 1 result
        response = client.table('users_prova_preferences').select(select_columns).eq(
            'user_id', # Column in your table that stores the user's UID (Ensure this column name is correct)
            user_id_key
        ).limit(1).execute() 

        # 3. Check if data was returned
        if not response.data:
            #print(f"No preferences found for user ID: {user_id_key}")
            return None, None
        
        # 4. Return the single result dictionary
        # response.data is a list of dictionaries, so we take the first element [0]
        preferences = response.data[0]
        gender = preferences.pop('gender', None)

        return preferences, gender
        
    except Exception as e:
        print(f"Error retrieving user preferences for {user_id_key}: {e}")
        return None, None