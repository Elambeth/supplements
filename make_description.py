import os
import sys
import time
import dotenv
from supabase import create_client, Client
from openai import OpenAI  # OpenAI client for DeepSeek API

# Make sure you have the OpenAI package installed:
# pip install openai>=1.0.0

# Load environment variables from .env file
dotenv.load_dotenv()

# Supabase configuration
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")  # New environment variable

if not supabase_url or not supabase_key:
    print("Error: Supabase environment variables not found.")
    exit(1)

if not deepseek_api_key:
    print("Error: DeepSeek API key not found in environment variables.")
    exit(1)

print(f"Connecting to Supabase at: {supabase_url}")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize the OpenAI client with DeepSeek API settings
client = OpenAI(
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com"  # DeepSeek API endpoint
)

def get_supplements_without_description(batch_size=10):
    """Get a batch of supplements without descriptions"""
    response = supabase.table('supplements') \
        .select('id, name, description') \
        .is_('description', 'null') \
        .order('id') \
        .limit(batch_size) \
        .execute()
    
    if hasattr(response, 'error') and response.error:
        print(f"Error fetching supplements: {response.error}")
        return []
    
    return response.data

def generate_description(supplement_name):
    """Generate a two-sentence description using DeepSeek V3 API"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # DeepSeek V3 model identifier
            messages=[
                {"role": "system", "content": "You are a knowledgeable nutritionist with expertise in dietary supplements. Provide informative, accurate, and concise information based on scientific consensus. Focus only on describing what supplements are and why people take them, without making claims about efficacy or recommendations."},
                {"role": "user", "content": f"Write a concise two-sentence description of {supplement_name} as a dietary supplement or physical intervention. The first sentence should factually explain what {supplement_name} is (its source, classification, or chemical nature). The second sentence should objectively state why people typically take it (common uses or purported benefits), without evaluating if these benefits are proven or worth pursuing. Maintain a neutral, educational tone."}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        # The OpenAI client formats the response in a consistent way
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating description: {e}")
        return None

def update_supplement_description(supplement_id, description):
    """Update the supplement description in the database"""
    try:
        response = supabase.table('supplements').update(
            {"description": description}
        ).eq('id', supplement_id).execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"Error updating description: {response.error}")
            return False
        
        return True
    except Exception as e:
        print(f"Error updating description: {e}")
        return False

def process_batch(batch_size=10, delay=1):
    """Process a batch of supplements without descriptions"""
    supplements = get_supplements_without_description(batch_size)
    
    if not supplements:
        print("No supplements without descriptions found.")
        return 0
    
    count_updated = 0
    print(f"Found {len(supplements)} supplements without descriptions.")
    
    for i, supplement in enumerate(supplements):
        supplement_id = supplement['id']
        supplement_name = supplement['name']
        
        print(f"\n[{i+1}/{len(supplements)}] Processing: {supplement_name} (ID: {supplement_id})")
        
        # Generate description
        print("Generating description using DeepSeek V3 API...")
        description = generate_description(supplement_name)
        
        if not description:
            print("Failed to generate description. Skipping.")
            continue
        
        print("\nGenerated description:")
        print("-" * 50)
        print(description)
        print("-" * 50)
        
        # Update the database
        success = update_supplement_description(supplement_id, description)
        if success:
            print("Description updated successfully!")
            count_updated += 1
        else:
            print("Failed to update description in the database.")
        
        # Add delay between API calls to avoid rate limiting
        if i < len(supplements) - 1:
            print(f"Waiting {delay} second(s) before next request...")
            time.sleep(delay)
    
    return count_updated

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_descriptions.py BATCH_SIZE [DELAY_SECONDS]")
        return
    
    try:
        batch_size = int(sys.argv[1])
        if batch_size <= 0:
            print("Batch size must be a positive integer.")
            return
    except ValueError:
        print(f"Error: Invalid batch size: {sys.argv[1]}")
        return
    
    # Optional delay parameter (defaults to 1 second)
    delay = 1
    if len(sys.argv) >= 3:
        try:
            delay = float(sys.argv[2])
            if delay < 0:
                print("Delay must be a non-negative number.")
                return
        except ValueError:
            print(f"Error: Invalid delay value: {sys.argv[2]}")
            return
    
    print(f"Starting batch processing with batch size: {batch_size}, delay: {delay} second(s)")
    
    # Process the batch
    count_updated = process_batch(batch_size, delay)
    
    print(f"\nBatch processing complete. Updated {count_updated} supplement descriptions.")

if __name__ == "__main__":
    main()