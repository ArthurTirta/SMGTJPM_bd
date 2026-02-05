from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google import genai
from google.genai import types
import os
import re
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.api.deps import get_db
from dotenv import load_dotenv

load_dotenv(override=True)

router = APIRouter()

API_KEY = settings.GOOGLE_API_KEY if hasattr(settings, 'GOOGLE_API_KEY') else os.getenv("GOOGLE_API_KEY")


# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class TestResponse(BaseModel):
    status: str

# Global variable to store database session for tool functions
_db_session = None

def is_safe_query(query: str) -> bool:
    """
    Validate that the query is safe (only SELECT operations).
    Returns True if safe, False otherwise.
    """
    # Remove comments and normalize whitespace
    query_cleaned = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query_cleaned = re.sub(r'/\*.*?\*/', '', query_cleaned, flags=re.DOTALL)
    query_cleaned = query_cleaned.strip().upper()
    
    # Check if query starts with SELECT
    if not query_cleaned.startswith('SELECT'):
        return False
    
    # List of dangerous keywords that should not appear in SELECT queries
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE',
        'EXEC', 'EXECUTE', 'CALL', 'INTO'
    ]
    
    # Check for dangerous keywords
    for keyword in dangerous_keywords:
        if re.search(r'\b' + keyword + r'\b', query_cleaned):
            return False
    
    return True

def execute_database_query(db: Session, query: str) -> dict:
    """
    Execute a read-only database query safely.
    Returns the query results or error message.
    """
    try:
        # Validate query safety
        if not is_safe_query(query):
            return {
                "success": False,
                "error": "Query is not allowed. Only SELECT queries are permitted.",
                "data": None
            }
        
        # Execute query with read-only transaction
        result = db.execute(text(query))
        
        # Fetch results
        rows = result.fetchall()
        columns = result.keys()
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            data.append(dict(zip(columns, row)))
        
        return {
            "success": True,
            "row_count": len(data),
            "data": data,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Database query error: {str(e)}",
            "data": None
        }

def generate_query_sql(query: str):
    """
    Execute a database query and return results.
    Only SELECT queries are allowed for security.
    """
    global _db_session
    
    if _db_session is None:
        return {
            "success": False,
            "error": "Database session not available",
            "data": None
        }
    
    result = execute_database_query(_db_session, query)
    return result

generate_query_sql_declaration = {
    "name":"generate_query_sql",
    "description": """Execute a READ-ONLY database query to retrieve information from the PostgreSQL database. 
    ONLY SELECT queries are allowed. Use this when you need to query jeans product data from the 'jeans' table.
    
    The jeans table contains columns: id, selling_price (JSON), discount, category_id, meta_info, product_id, 
    pdp_url, sku, brand, department_id, last_seen_date, launch_on, mrp (JSON), product_name, feature_image_s3, 
    channel_id, feature_list (JSON), description, style_attributes (JSON), pdp_images_s3 (JSON).
    
    For JSON fields like selling_price and mrp, use PostgreSQL JSON operators:
    - selling_price->>'USD' to extract USD value as text
    - (selling_price->>'USD')::numeric to extract as number for calculations
    
    Always use proper SQL syntax with correct table and column names.""",
    "parameters": {
        "type":"object",
        "properties":{
            "query": {
                "type":"string",
                "description": """A valid PostgreSQL SELECT query for the 'jeans' table. 
                Examples:
                - 'SELECT * FROM jeans LIMIT 10'
                - 'SELECT brand, product_name, (selling_price->>''USD'')::numeric as price FROM jeans WHERE brand = ''RALPH LAUREN'' LIMIT 10'
                - 'SELECT brand, COUNT(*) as total FROM jeans GROUP BY brand'
                - 'SELECT * FROM jeans WHERE discount > 0 ORDER BY discount DESC LIMIT 10'
                
                Only SELECT statements are allowed - no INSERT, UPDATE, DELETE, or other modification operations."""
            }
        },
        "required":["query"]
    }
}


# Load database schema documentation
models_database = ""
documentation_path = os.path.join(os.path.dirname(__file__), "database_schema.md")

try:
    with open(documentation_path, 'r', encoding='utf-8') as f:
        models_database = f.read()
    print(f"✓ Successfully loaded database schema documentation from: {documentation_path}")
except FileNotFoundError:
    print(f"⚠ Warning: Database schema file not found at: {documentation_path}")
    models_database = "Database schema documentation not available. Please ensure database_schema.md exists."
except Exception as e:
    print(f"⚠ Warning: Error loading database schema: {str(e)}")
    models_database = "Database schema documentation could not be loaded."

system_prompt = f"""You are acting as an AI assistant for a jeans e-commerce database. 
You are answering questions about jeans products in the database, including product information, brands, prices, and specifications.

Your responsibility is to help users query and understand the jeans product data. 
Be professional, accurate, and helpful in your responses.

If you need specific data from the database, use your generate_query_sql tool to query the database.

IMPORTANT DATABASE QUERY GUIDELINES:
- You can ONLY use SELECT queries to read data from the database
- NO INSERT, UPDATE, DELETE, or any data modification operations are allowed
- The main table is 'jeans' - always query from this table
- Always use proper PostgreSQL syntax
- Use LIMIT clause to avoid retrieving too many rows (e.g., LIMIT 10 or LIMIT 100)
- When querying JSON fields like selling_price or mrp, use PostgreSQL JSON operators:
  * selling_price->>'USD' to get USD value as text
  * (selling_price->>'USD')::numeric to get USD value as number
- Common queries include filtering by brand, price range, discount, dates, etc.
- When showing prices, always format them nicely with currency symbols

## Database Schema:
{models_database}

With this context, please help users explore and query the jeans product database."""


client = genai.Client(api_key=API_KEY)

tools = types.Tool(
    function_declarations=[generate_query_sql_declaration])

config = types.GenerateContentConfig(tools=[tools], system_instruction=system_prompt)


def handle_tool_calls(function_calls):
    """Handle function calls from Gemini API"""
    results = []
    for function_call in function_calls:
        tool_name = function_call.name
        arguments = dict(function_call.args)
        print(f"🔨 Tool called: {tool_name} with args: {arguments}", flush=True)
        
        # Execute the function
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {"error": "Function not found"}
        print(f"📊 Tool result: {result}", flush=True)
        
        # Create function response
        function_response = types.FunctionResponse(
            name=tool_name,
            response={"result": result}
        )
        results.append(function_response)
    
    return results

# Test route untuk memastikan server berjalanf
@router.get('/test', response_model=TestResponse, tags=["AI"])
def test():
    """Test endpoint to check if AI service is running"""
    return TestResponse(status='AI Backend is running!')

@router.post('/chat', response_model=ChatResponse, tags=["AI"])
def get_response(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with AI assistant about jeans products database.
    
    Send a message and get an AI-generated response based on jeans product data.
    The AI can query the database to answer your questions about products, brands, prices, and more.
    
    Example questions:
    - "Show me all RALPH LAUREN jeans"
    - "What jeans have discounts?"
    - "List the most expensive jeans"
    - "How many jeans are in the database?"
    """
    global _db_session
    _db_session = db  # Store db session for tool functions
    
    try:
        # Validate request data
        if not request.message:
            raise HTTPException(status_code=400, detail='Message is required')
            
        user_message = request.message
        print(f"📩 Received message: {user_message}")
        
        # Initialize Gemini session with tools
        session = client.models.generate_content(
            model="gemini-3-flash-preview",
            config=config,
            contents=user_message
        )
        
        # Send initial message
        response = session
        
        # Function calling loop
        max_iterations = 5
        iteration_count = 0
        done = False
        
        while not done and iteration_count < max_iterations:
            iteration_count += 1
            
            # Check if model wants to call functions
            if not response.candidates or len(response.candidates) == 0:
                break
            
            # Check for function calls
            function_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
            
            if function_calls:
                print(f"🔧 Iteration {iteration_count}: Executing {len(function_calls)} function call(s)")
                
                # Execute function calls
                function_responses = handle_tool_calls(function_calls)
                
                # Send function responses back to model using generate_content again
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",         
                    config=config,
                    contents=[
                        user_message,
                        response.candidates[0].content,
                        types.Content(
                            parts=[types.Part(function_response=fr) for fr in function_responses]
                        )
                    ]
                )
            else:
                done = True
        
        # Extract final text response
        final_text = response.text if response and hasattr(response, 'text') else "No response generated"
        print(f"✅ Sending response: {final_text[:100]}...")
        
        return ChatResponse(response=final_text)
        
    except Exception as e:
        print(f"❌ Error in get_response: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
    finally:
        _db_session = None