import re
import logging
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum number of rows to return
MAX_ROWS = 5000

# Forbidden SQL tokens (case insensitive)
FORBIDDEN_TOKENS = [
    r'\bATTACH\b',
    r'\bPRAGMA\b', 
    r'\bCOPY\b',
    r'\bEXPORT\b',
    r'\bINSERT\b',
    r'\bUPDATE\b',
    r'\bDELETE\b',
    r'\bDROP\b',
    r'\bALTER\b',
    r'\bCREATE\s+TABLE\b'
]

# Fallback queries for common scenarios
FALLBACK_QUERIES = {
    "monthly_category": """
        select month, category, sum(revenue) as total_revenue
        from sales_with_month
        group by 1,2
        order by 1,2;
    """,
    "channel_sales": """
        select sales_channel, sum(revenue) as total_revenue
        from sales
        group by 1
        order by total_revenue desc;
    """,
    "region_sales": """
        select region, sum(revenue) as total_revenue
        from sales
        group by 1
        order by total_revenue desc;
    """
}


class SQLValidationError(Exception):
    """Exception raised when SQL validation fails"""
    pass


def validate_sql(sql: str) -> None:
    """
    Validate SQL query against security rules
    
    Args:
        sql: SQL query string to validate
        
    Raises:
        SQLValidationError: If SQL query is invalid or contains forbidden tokens
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query")
    
    sql_clean = sql.strip()
    
    # Check if it's a SELECT statement
    if not re.match(r'^\s*select\b', sql_clean, re.IGNORECASE):
        raise SQLValidationError("Only SELECT statements are allowed")
    
    # Check for forbidden tokens
    for token_pattern in FORBIDDEN_TOKENS:
        if re.search(token_pattern, sql_clean, re.IGNORECASE):
            raise SQLValidationError(f"Forbidden token detected: {token_pattern}")
    
    logger.info("SQL validation passed")


def add_limit_if_needed(sql: str) -> str:
    """
    Add LIMIT clause to queries without GROUP BY to prevent large result sets
    
    Args:
        sql: SQL query string
        
    Returns:
        SQL query with LIMIT added if needed
    """
    sql_clean = sql.strip()
    
    # Check if query already has LIMIT
    if re.search(r'\bLIMIT\s+\d+\b', sql_clean, re.IGNORECASE):
        return sql_clean
    
    # Check if query has GROUP BY (aggregation queries don't need LIMIT)
    if re.search(r'\bGROUP\s+BY\b', sql_clean, re.IGNORECASE):
        return sql_clean
    
    # Add LIMIT to the end of the query
    # Remove trailing semicolon if present
    if sql_clean.endswith(';'):
        sql_clean = sql_clean[:-1]
    
    return f"{sql_clean} LIMIT {MAX_ROWS};"


def sanitize_sql(sql: str) -> str:
    """
    Sanitize and validate SQL query
    
    Args:
        sql: Raw SQL query from LLM
        
    Returns:
        Sanitized and validated SQL query
        
    Raises:
        SQLValidationError: If validation fails
    """
    try:
        # Basic cleanup
        sql_clean = sql.strip()
        if sql_clean.startswith('```sql'):
            sql_clean = sql_clean[6:]
        if sql_clean.endswith('```'):
            sql_clean = sql_clean[:-3]
        sql_clean = sql_clean.strip()
        
        # Validate the SQL
        validate_sql(sql_clean)
        
        # Add LIMIT if needed
        sql_with_limit = add_limit_if_needed(sql_clean)
        
        logger.info(f"SQL sanitized successfully: {sql_with_limit[:100]}...")
        return sql_with_limit
        
    except Exception as e:
        logger.error(f"SQL sanitization failed: {e}")
        raise SQLValidationError(f"SQL validation failed: {str(e)}")


def get_fallback_query(question: str) -> str:
    """
    Get a fallback query based on the user's question
    
    Args:
        question: User's natural language question
        
    Returns:
        Fallback SQL query
    """
    question_lower = question.lower()
    
    # Check for specific region queries
    region_keywords = {
        '北部': 'North',
        'north': 'North', 
        '北': 'North',
        '南部': 'South',
        'south': 'South',
        '南': 'South', 
        '東部': 'East',
        'east': 'East',
        '東': 'East',
        '西部': 'West', 
        'west': 'West',
        '西': 'West'
    }
    
    for keyword, region_name in region_keywords.items():
        if keyword in question_lower:
            return f"""
                select region, sum(revenue) as total_revenue
                from sales
                where region = '{region_name}'
                group by 1
                order by total_revenue desc;
            """
    
    # Check for monthly/time-based questions
    if any(keyword in question_lower for keyword in ['月', 'month', '月毎', '月別', 'monthly']):
        if any(keyword in question_lower for keyword in ['カテゴリ', 'category', 'categories']):
            return FALLBACK_QUERIES["monthly_category"]
    
    # Check for channel-related questions
    if any(keyword in question_lower for keyword in ['チャネル', 'channel', 'channels', 'sales_channel', 'オンライン', 'online', '店舗', 'store']):
        return FALLBACK_QUERIES["channel_sales"]
    
    # Check for general region-related questions
    if any(keyword in question_lower for keyword in ['地域', 'region', 'regions', '地方']):
        return FALLBACK_QUERIES["region_sales"]
    
    # Check for category-related questions
    if any(keyword in question_lower for keyword in ['カテゴリ', 'category', 'categories', 'electronics', 'clothing', 'beauty', 'groceries']):
        return """
            select category, sum(revenue) as total_revenue
            from sales
            group by 1
            order by total_revenue desc;
        """
    
    # Default fallback - general summary
    return FALLBACK_QUERIES["region_sales"]


def process_sql_safely(sql: str, question: str = "") -> str:
    """
    Process SQL query safely with fallback handling
    
    Args:
        sql: SQL query from LLM
        question: Original user question for fallback selection
        
    Returns:
        Safe SQL query (sanitized or fallback)
    """
    try:
        return sanitize_sql(sql)
    except SQLValidationError as e:
        logger.warning(f"SQL validation failed, using fallback: {e}")
        return get_fallback_query(question)
    except Exception as e:
        logger.error(f"Unexpected error in SQL processing: {e}")
        return get_fallback_query(question)