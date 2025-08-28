import os
import logging
from typing import Optional
from abc import ABC, abstractmethod

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters"""
    
    @abstractmethod
    def generate_sql(self, question: str, schema: str) -> str:
        """Generate SQL query from natural language question"""
        pass
    
    @abstractmethod
    def summarize(self, sql: str, data_preview: str) -> str:
        """Generate summary of SQL results"""
        pass


class OpenAIAdapter(LLMAdapter):
    """OpenAI GPT adapter"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if openai is None:
            raise ImportError("openai package not installed. Install with: pip install openai")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def generate_sql(self, question: str, schema: str) -> str:
        """Generate SQL query from natural language question"""
        system_prompt = f"""You are a careful data analyst. Convert the user's question into a single DuckDB SQL query.
Rules:
- Use only the table 'sales' and helper view 'sales_with_month'.
- SELECT only. No PRAGMA/ATTACH/INSERT/UPDATE/DELETE/COPY/EXPORT/CREATE TABLE.
- Prefer clear GROUP BY and snake_case aliases.
- For monthly questions, use sales_with_month.month.
- When returning raw rows, add LIMIT 5000.
- Return ONLY SQL, no explanations or markdown.

Schema:
{schema}

Examples:
Q: 月毎のカテゴリー別の売上
SQL:
select month, category, sum(revenue) as total_revenue
from sales_with_month
group by 1,2
order by 1,2;

Q: チャネルごとの売上
SQL:
select sales_channel, sum(revenue) as total_revenue
from sales
group by 1
order by total_revenue desc;

Q: 地域ごとの売上の合計
SQL:
select region, sum(revenue) as total_revenue
from sales
group by 1
order by total_revenue desc;"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.1,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def summarize(self, sql: str, data_preview: str) -> str:
        """Generate summary of SQL results"""
        prompt = f"""以下のSQLクエリと結果データをもとに、日本語で一段落の要約を生成してください。数値は桁区切りを含めて読みやすくしてください。過度な断定は避け、データの特徴や傾向を簡潔に述べてください。

SQL:
{sql}

データ (先頭部分):
{data_preview}

要約:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI summarization error: {e}")
            raise


class AnthropicAdapter(LLMAdapter):
    """Anthropic Claude adapter"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        if anthropic is None:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def generate_sql(self, question: str, schema: str) -> str:
        """Generate SQL query from natural language question"""
        system_prompt = f"""You are a careful data analyst. Convert the user's question into a single DuckDB SQL query.
Rules:
- Use only the table 'sales' and helper view 'sales_with_month'.
- SELECT only. No PRAGMA/ATTACH/INSERT/UPDATE/DELETE/COPY/EXPORT/CREATE TABLE.
- Prefer clear GROUP BY and snake_case aliases.
- For monthly questions, use sales_with_month.month.
- When returning raw rows, add LIMIT 5000.
- Return ONLY SQL, no explanations or markdown.

Schema:
{schema}

Examples:
Q: 月毎のカテゴリー別の売上
SQL:
select month, category, sum(revenue) as total_revenue
from sales_with_month
group by 1,2
order by 1,2;

Q: チャネルごとの売上
SQL:
select sales_channel, sum(revenue) as total_revenue
from sales
group by 1
order by total_revenue desc;

Q: 地域ごとの売上の合計
SQL:
select region, sum(revenue) as total_revenue
from sales
group by 1
order by total_revenue desc;"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": question}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def summarize(self, sql: str, data_preview: str) -> str:
        """Generate summary of SQL results"""
        prompt = f"""以下のSQLクエリと結果データをもとに、日本語で一段落の要約を生成してください。数値は桁区切りを含めて読みやすくしてください。過度な断定は避け、データの特徴や傾向を簡潔に述べてください。

SQL:
{sql}

データ (先頭部分):
{data_preview}

要約:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic summarization error: {e}")
            raise


def create_llm_adapter() -> LLMAdapter:
    """Factory function to create LLM adapter based on environment variables"""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - falling back to mock responses")
            return MockLLMAdapter()
        return OpenAIAdapter(api_key, model)
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set - falling back to mock responses")
            return MockLLMAdapter()
        return AnthropicAdapter(api_key, model)
    
    else:
        logger.warning(f"Unknown LLM provider: {provider} - falling back to mock responses")
        return MockLLMAdapter()


class MockLLMAdapter(LLMAdapter):
    """Mock LLM adapter for testing without API keys"""
    
    def generate_sql(self, question: str, schema: str) -> str:
        """Generate SQL query from natural language question using simple heuristics"""
        question_lower = question.lower()
        
        # Specific region queries - map Japanese terms to English region names
        region_map = {
            '北部': 'North', '北': 'North', 'north': 'North',
            '南部': 'South', '南': 'South', 'south': 'South', 
            '東部': 'East', '東': 'East', 'east': 'East',
            '西部': 'West', '西': 'West', 'west': 'West'
        }
        
        for keyword, region in region_map.items():
            if keyword in question_lower:
                return f"SELECT region, SUM(revenue) as total_revenue FROM sales WHERE region = '{region}' GROUP BY 1 ORDER BY total_revenue DESC"
        
        # Monthly category analysis
        if any(k in question_lower for k in ['月', 'month', '月毎', '月別']) and any(k in question_lower for k in ['カテゴリ', 'category']):
            return "SELECT month, category, SUM(revenue) as total_revenue FROM sales_with_month GROUP BY 1,2 ORDER BY 1,2"
        
        # Channel analysis
        if any(k in question_lower for k in ['チャネル', 'channel', 'オンライン', 'online', '店舗', 'store']):
            return "SELECT sales_channel, SUM(revenue) as total_revenue FROM sales GROUP BY 1 ORDER BY total_revenue DESC"
        
        # Category analysis
        if any(k in question_lower for k in ['カテゴリ', 'category', 'electronics', 'clothing']):
            return "SELECT category, SUM(revenue) as total_revenue FROM sales GROUP BY 1 ORDER BY total_revenue DESC"
        
        # Region analysis (general)
        if any(k in question_lower for k in ['地域', 'region', '地方']):
            return "SELECT region, SUM(revenue) as total_revenue FROM sales GROUP BY 1 ORDER BY total_revenue DESC"
        
        # Default to region summary
        return "SELECT region, SUM(revenue) as total_revenue FROM sales GROUP BY 1 ORDER BY total_revenue DESC"
    
    def summarize(self, sql: str, data_preview: str) -> str:
        """Generate simple summary without LLM"""
        if "where region" in sql.lower():
            if "north" in sql.lower():
                return "北部地域の売上データを分析しました。表とグラフから詳細な売上状況を確認できます。"
            elif "south" in sql.lower():
                return "南部地域の売上データを分析しました。表とグラフから詳細な売上状況を確認できます。"
            elif "east" in sql.lower():
                return "東部地域の売上データを分析しました。表とグラフから詳細な売上状況を確認できます。"
            elif "west" in sql.lower():
                return "西部地域の売上データを分析しました。表とグラフから詳細な売上状況を確認できます。"
        
        if "sales_channel" in sql.lower():
            return "販売チャネル別の売上データを分析しました。オンラインと店舗の売上を比較できます。"
        
        if "category" in sql.lower():
            return "カテゴリ別の売上データを分析しました。各商品カテゴリの売上実績を確認できます。"
        
        if "month" in sql.lower():
            return "月次売上トレンドを分析しました。時系列での売上推移を確認できます。"
        
        return "売上データの分析結果を表とグラフで確認できます。詳細な数値は上記の表をご参照ください。"


# Convenience functions
def generate_sql(question: str, schema: str) -> str:
    """Generate SQL query from natural language question"""
    adapter = create_llm_adapter()
    return adapter.generate_sql(question, schema)


def summarize(sql: str, data_preview: str) -> str:
    """Generate summary of SQL results"""
    adapter = create_llm_adapter()
    return adapter.summarize(sql, data_preview)