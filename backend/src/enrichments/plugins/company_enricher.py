"""
Company information enrichment plugin.
Extracts structured company data like CEO, revenue, industry, etc.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import re
import logging

from ..engine import EnrichmentPlugin, EnrichmentResult

logger = logging.getLogger(__name__)


class CompanyEnricher(EnrichmentPlugin):
    """
    Extract company information from text content.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.use_llm = config.get("use_llm", False) if config else False

    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """
        Extract company information from content.

        Extracts:
        - Company name
        - CEO/Founder
        - Revenue
        - Employee count
        - Industry
        - Founded year
        - Headquarters location
        """
        result = EnrichmentResult(self.name)

        try:
            if self.use_llm:
                # Use LLM for extraction
                data = await self._extract_with_llm(content)
            else:
                # Use pattern matching
                data = await self._extract_with_patterns(content)

            result.data = data
            result.success = bool(data)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Company enrichment failed: {e}")

        return result

    async def _extract_with_patterns(self, content: str) -> Dict[str, Any]:
        """Extract company info using regex patterns."""
        data = {}

        # CEO / Founder patterns
        ceo_patterns = [
            r"CEO[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
            r"Chief Executive Officer[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
            r"founder[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
            r"founded by ([A-Z][a-z]+ [A-Z][a-z]+)",
        ]
        for pattern in ceo_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data["ceo"] = match.group(1)
                break

        # Revenue patterns
        revenue_patterns = [
            r"revenue[:\s]+\$?([\d.]+)\s*(billion|million|B|M)",
            r"annual revenue[:\s]+\$?([\d.]+)\s*(billion|million|B|M)",
            r"\$?([\d.]+)\s*(billion|million|B|M)\s+in revenue",
        ]
        for pattern in revenue_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount = match.group(1)
                unit = match.group(2).lower()
                if unit in ["billion", "b"]:
                    data["revenue"] = f"${amount}B"
                else:
                    data["revenue"] = f"${amount}M"
                break

        # Employee count patterns
        employee_patterns = [
            r"(\d+[\d,]*)\s+employees",
            r"employee count[:\s]+(\d+[\d,]*)",
            r"workforce of (\d+[\d,]*)",
        ]
        for pattern in employee_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data["employees"] = match.group(1).replace(",", "")
                break

        # Founded year patterns
        founded_patterns = [
            r"founded in (\d{4})",
            r"established in (\d{4})",
            r"since (\d{4})",
        ]
        for pattern in founded_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data["founded"] = match.group(1)
                break

        # Headquarters patterns
        hq_patterns = [
            r"headquartered in ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
            r"headquarters[:\s]+([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
            r"based in ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
        ]
        for pattern in hq_patterns:
            match = re.search(pattern, content)
            if match:
                data["headquarters"] = match.group(1)
                break

        # Industry patterns
        industry_keywords = {
            "technology": ["software", "tech", "saas", "cloud", "ai", "machine learning"],
            "finance": ["bank", "financial", "fintech", "investment", "insurance"],
            "healthcare": ["health", "medical", "pharmaceutical", "biotech", "hospital"],
            "retail": ["retail", "e-commerce", "ecommerce", "shopping", "store"],
            "manufacturing": ["manufacturing", "factory", "industrial", "production"],
            "energy": ["energy", "oil", "gas", "renewable", "solar", "wind"],
            "telecommunications": ["telecom", "wireless", "network", "broadband"],
            "automotive": ["automotive", "car", "vehicle", "transportation"],
        }

        content_lower = content.lower()
        for industry, keywords in industry_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                data["industry"] = industry
                break

        return data

    async def _extract_with_llm(self, content: str) -> Dict[str, Any]:
        """Extract company info using LLM."""
        # TODO: Integrate with Instructor + OpenAI/Anthropic
        # For now, fall back to pattern matching
        return await self._extract_with_patterns(content)

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return {
            "type": "object",
            "properties": {
                "ceo": {
                    "type": "string",
                    "description": "CEO or founder name",
                },
                "revenue": {
                    "type": "string",
                    "description": "Annual revenue (e.g., $1.5B)",
                },
                "employees": {
                    "type": "string",
                    "description": "Number of employees",
                },
                "founded": {
                    "type": "string",
                    "description": "Year founded",
                },
                "headquarters": {
                    "type": "string",
                    "description": "Headquarters location",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry category",
                },
            },
        }


class CompanyFinancialEnricher(EnrichmentPlugin):
    """
    Extract detailed financial information for companies.
    """

    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """Extract financial metrics."""
        result = EnrichmentResult(self.name)

        try:
            data = {}

            # Market cap pattern
            market_cap_patterns = [
                r"market cap[italization]*[:\s]+\$?([\d.]+)\s*(billion|million|trillion|B|M|T)",
                r"valued at \$?([\d.]+)\s*(billion|million|trillion|B|M|T)",
            ]
            for pattern in market_cap_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    amount = match.group(1)
                    unit = match.group(2).lower()
                    if unit in ["trillion", "t"]:
                        data["market_cap"] = f"${amount}T"
                    elif unit in ["billion", "b"]:
                        data["market_cap"] = f"${amount}B"
                    else:
                        data["market_cap"] = f"${amount}M"
                    break

            # Profit/earnings patterns
            profit_patterns = [
                r"profit[:\s]+\$?([\d.]+)\s*(billion|million|B|M)",
                r"net income[:\s]+\$?([\d.]+)\s*(billion|million|B|M)",
            ]
            for pattern in profit_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    amount = match.group(1)
                    unit = match.group(2).lower()
                    if unit in ["billion", "b"]:
                        data["profit"] = f"${amount}B"
                    else:
                        data["profit"] = f"${amount}M"
                    break

            # Growth rate patterns
            growth_patterns = [
                r"(\d+)%\s+(?:annual\s+)?growth",
                r"growing at (\d+)%",
                r"growth rate[:\s]+(\d+)%",
            ]
            for pattern in growth_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    data["growth_rate"] = f"{match.group(1)}%"
                    break

            result.data = data
            result.success = bool(data)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Financial enrichment failed: {e}")

        return result

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return {
            "type": "object",
            "properties": {
                "market_cap": {
                    "type": "string",
                    "description": "Market capitalization",
                },
                "profit": {
                    "type": "string",
                    "description": "Net profit/income",
                },
                "growth_rate": {
                    "type": "string",
                    "description": "Annual growth rate",
                },
            },
        }
