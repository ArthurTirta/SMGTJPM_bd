from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google import genai
from google.genai import types
import os
import re
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.core.config import settings
from app.api.deps import get_db
from dotenv import load_dotenv
from rich import print as rprint

load_dotenv(override=True)

router = APIRouter()

API_KEY = settings.GOOGLE_API_KEY if hasattr(settings, 'GOOGLE_API_KEY') else os.getenv("GOOGLE_API_KEY")


# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    user_location: str = ""  # halaman user saat ini, e.g. "Home", "Ecommerce (Daftar Produk)"

class ChatResponse(BaseModel):
    response: Optional[str] = None
    buttons: Optional[list[dict[str, str]]] = None

class TestResponse(BaseModel):
    status: str


# Global variables
_db_session = None
final_text = {}  # Global dict untuk menyimpan response


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


def _json_serializable(value):
    """Convert value to JSON-serializable type (Decimal, date, datetime -> str/float)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_serializable(v) for v in value]
    return value


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
        
        # Convert to list of dictionaries (nilai Decimal/datetime dibuat JSON-serializable)
        data = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            data.append(
                {k: _json_serializable(v) for k, v in row_dict.items()}
            )
        
        return {
            "success": True,
            "row_count": len(data),
            "data": data,
            "error": None
        }
        
    except Exception as e:
        # Rollback transaksi agar session bisa dipakai lagi untuk query berikutnya
        db.rollback()
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
    "name": "generate_query_sql",
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
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": """A valid PostgreSQL SELECT query for the 'jeans' table. 
                Examples:
                - 'SELECT * FROM jeans LIMIT 10'
                - 'SELECT brand, product_name, (selling_price->>''USD'')::numeric as price FROM jeans WHERE brand = ''RALPH LAUREN'' LIMIT 10'
                - 'SELECT brand, COUNT(*) as total FROM jeans GROUP BY brand'
                - 'SELECT * FROM jeans WHERE discount > 0 ORDER BY discount DESC LIMIT 10'
                
                Only SELECT statements are allowed - no INSERT, UPDATE, DELETE, or other modification operations."""
            }
        },
        "required": ["query"]
    }
}


def generate_button(buttons: list[dict[str, str]]) -> dict:
    """
    Add buttons to final_text response.
    This function is called by AI when it wants to generate navigation buttons.
    After calling this, you MUST still provide a text response to the user.
    """
    global final_text
    final_text["buttons"] = buttons
    # Return minimal acknowledgment - AI should continue with text response
    return {
        "success": True, 
        "message": "Buttons prepared. Now provide your text response to the user."
    }


generate_button_declaration = {
    "name": "generate_button",
    "description": """Generate navigation buttons to help users navigate to relevant pages.
    
    IMPORTANT: This tool only prepares buttons - you MUST still provide a text response to the user!
    
    Use this when you want to direct users to specific product details, search results, or other pages.
    
    Workflow:
    1. Call this tool to prepare buttons
    2. Then provide your text response explaining what you found/suggesting
    3. The buttons will appear below your text message
    
    Examples:
    - When showing a specific product, add a button to view its detail page: /ecommerce/{id}
    - When discussing multiple products, add buttons to view each product
    - When talking about browsing all products, add a button to /ecommerce
    - For filtering by brand, add button like /ecommerce?brand=RALPH+LAUREN
    
    URL format examples:
    - Product detail: /ecommerce/123 (where 123 is the product id)
    - Product list: /ecommerce
    - Filtered list: /ecommerce?brand=NIKE or /ecommerce?search=skinny
    - Home page: /
    - Games page: /games
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "buttons": { 
                "type": "array",
                "description": "List of buttons with text and URL to direct users to relevant pages",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {  
                            "type": "string",
                            "description": "The text displayed on the button (e.g., 'View Product Details', 'Browse All Jeans')"
                        },
                        "url": {  
                            "type": "string",
                            "description": "The URL path to navigate to (e.g., '/ecommerce/123', '/ecommerce', '/games')"
                        }
                    },
                    "required": ["text", "url"] 
                }
            }
        },
        "required": ["buttons"]
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


system_prompt = f"""You are an assistant for the SMGT organization website, which educates children. Your focus changes based on the user's current page.

CRITICAL RESPONSE RULES:
- ALWAYS provide a text response to the user's question
- Buttons are OPTIONAL - only use generate_button tool when it adds value
- If you use generate_button, you MUST still provide text response after
- Never provide buttons without text explanation

1. **E-commerce Page**
   When the user is on the e-commerce page, help them find jeans products using the database.
   
   - You can query the database using the generate_query_sql tool
   - ONLY use SELECT queries (no INSERT, UPDATE, DELETE)
   - Always use LIMIT to avoid retrieving too many rows
   - For JSON fields like selling_price, use PostgreSQL operators: selling_price->>'USD'
   
   Response Pattern:
   1. Answer the user's question with text
   2. Optionally, if helpful, call generate_button to add navigation buttons
   3. The buttons will appear below your text response
   
   Example workflow for "Show me RALPH LAUREN jeans":
   - Call generate_query_sql to get products
   - Write text: "I found 3 RALPH LAUREN jeans: [list products]"
   - Optionally call generate_button with product detail links
   
   Button usage (optional):
   - Product detail button: /ecommerce/{{product_id}} (e.g., /ecommerce/123)
   - Browse all: /ecommerce
   - Filtered search: /ecommerce?brand=RALPH+LAUREN

2. **Home Page**
   Introduce SMGT: an organization for children's education to empower children to be kind throughout their lives in peace, loving God Jesus Christ and Family.
   
   Website features:
   - Games: /games (educational games for children)
   - E-commerce: /ecommerce (support the organization)
   
   You can optionally use generate_button to create navigation buttons for these features, but ALWAYS provide text explanation first.

3. **Games Page**
   Introduce available games:
   - Learn English: an assistant to improve English skills
   
   Mention more games coming soon.

## Database Schema:
{models_database}

Remember: 
- Text response is MANDATORY
- Buttons are OPTIONAL (only when they add value)
- If you use buttons, provide text explanation first"""


client = genai.Client(api_key=API_KEY)

tools = types.Tool(
    function_declarations=[generate_query_sql_declaration, generate_button_declaration]
)

config = types.GenerateContentConfig(
    tools=[tools], 
    system_instruction=system_prompt
)


def handle_tool_calls(function_calls):
    """Handle function calls from Gemini API"""
    results = []
    for function_call in function_calls:
        tool_name = function_call.name
        arguments = dict(function_call.args)
        print(f"🔨 Tool called: {tool_name} with args: {arguments}", flush=True)
        
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {"error": "Function not found"}
        print(f"📊 Tool result: {result}", flush=True)
        
        function_response = types.FunctionResponse(
            name=tool_name,
            response={"result": result}
        )
        
        results.append(function_response)
    
    return results


@router.get('/test', response_model=TestResponse, tags=["AI"])
def test():
    """Test endpoint to check if AI service is running"""
    return TestResponse(status='AI Backend is running!')


@router.post('/chat', response_model=ChatResponse, tags=["AI"])
def get_response(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a message and get an AI-generated response with optional navigation buttons.
    
    The AI can:
    - Query the database for product information
    - Generate navigation buttons to help users explore
    - Adapt responses based on the user's current page
    
    Example questions:
    - "Show me RALPH LAUREN jeans"
    - "What jeans have discounts?"
    - "Tell me about SMGT"
    """
    global _db_session, final_text
    _db_session = db
    final_text = {}  # Reset final_text untuk setiap request
    
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail='Message is required')
            
        user_message = request.message
        user_location = (request.user_location or "").strip()
        
        # Include user location in context
        if user_location:
            context_message = f"[User is currently on page: {user_location}]\n\n{user_message}"
            print(f"📩 Received message (location={user_location!r}): {user_message}")
        else:
            context_message = user_message
            print(f"📩 Received message: {user_message}")
        
        history = [types.Content(role="user", parts=[types.Part(text=context_message)])]
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            config=config,
            contents=history
        )
        
        max_iterations = 5
        iteration_count = 0
        done = False
        
        while not done and iteration_count < max_iterations:
            iteration_count += 1
            
            if not response.candidates or len(response.candidates) == 0:
                break
            
            model_content = response.candidates[0].content
            history.append(model_content)

            # Check for function calls
            function_calls = []
            for part in model_content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
            
            if function_calls:
                print(f"🔧 Iteration {iteration_count}: Executing {len(function_calls)} function call(s)")
                
                function_responses = handle_tool_calls(function_calls)

                response_content = types.Content(
                    role="user",
                    parts=[types.Part(function_response=fr) for fr in function_responses]
                )
                history.append(response_content)
                
                # Send the updated history back to the model
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",         
                    config=config,
                    contents=history
                )
            else:
                done = True
        
        # Extract final text response
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    final_text["response"] = part.text
                    break
        
        # Prepare response
        response_text = final_text.get("response")
        response_buttons = final_text.get("buttons")
        
        # FALLBACK: If buttons exist but no text, create default text
        if response_buttons and not response_text:
            response_text = "Here are some options for you:"
            print("⚠️ Warning: AI provided buttons without text response. Using fallback.")
        
        # Log final response
        print(f"✅ Final response:")
        print(f"   Text: {response_text[:100] if response_text else 'None'}...")
        print(f"   Buttons: {len(response_buttons) if response_buttons else 0}")
        
        return ChatResponse(
            response=response_text,
            buttons=response_buttons
        )
        
    except Exception as e:
        print(f"❌ Error in get_response: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
    finally:
        _db_session = None
        final_text = {}  # Reset after response