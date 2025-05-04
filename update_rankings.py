import os
import dotenv
from supabase import create_client, Client

# Load environment variables from .env file
dotenv.load_dotenv()

# Supabase configuration
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Supabase environment variables not found.")
    exit(1)

print(f"Connecting to Supabase at: {supabase_url}")
supabase: Client = create_client(supabase_url, supabase_key)

def update_rankings():
    print("Updating research rankings...")
    
    # Get all research data ordered by count - FIXED SYNTAX
    response = supabase.table('supplement_research').select('id, research_count').order('research_count', desc=True).execute()
    
    if hasattr(response, 'error') and response.error:
        print(f"Error fetching research data: {response.error}")
        return False
    
    research_data = response.data
    total_count = len(research_data)
    
    print(f"Found {total_count} supplements with research data")
    
    # Calculate and update rankings
    for position, item in enumerate(research_data, 1):
        supplement_research_id = item['id']
        percentile = round((1 - (position / total_count)) * 100)
        
        print(f"Updating rank for ID {supplement_research_id}: Position {position}, Percentile {percentile}%")
        
        # Update the database
        update_response = supabase.table('supplement_research').update({
            'rank_position': position,
            'rank_total': total_count,
            'rank_percentile': percentile
        }).eq('id', supplement_research_id).execute()
        
        if hasattr(update_response, 'error') and update_response.error:
            print(f"Error updating ranking for ID {supplement_research_id}: {update_response.error}")
    
    print("Rankings updated successfully!")
    return True

if __name__ == "__main__":
    update_rankings()