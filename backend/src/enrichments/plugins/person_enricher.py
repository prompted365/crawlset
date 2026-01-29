"""
Person information enrichment plugin.
Extracts structured person data like role, company, social profiles, etc.
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import re
import logging

from ..engine import EnrichmentPlugin, EnrichmentResult

logger = logging.getLogger(__name__)


class PersonEnricher(EnrichmentPlugin):
    """
    Extract person information from text content.
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
        Extract person information from content.

        Extracts:
        - Name
        - Job title/role
        - Company
        - Location
        - Education
        - Social profiles (LinkedIn, Twitter, etc.)
        - Contact information
        """
        result = EnrichmentResult(self.name)

        try:
            if self.use_llm:
                data = await self._extract_with_llm(content)
            else:
                data = await self._extract_with_patterns(content)

            result.data = data
            result.success = bool(data)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Person enrichment failed: {e}")

        return result

    async def _extract_with_patterns(self, content: str) -> Dict[str, Any]:
        """Extract person info using regex patterns."""
        data = {}

        # Name patterns (look for capitalized names)
        name_patterns = [
            r"^([A-Z][a-z]+ [A-Z][a-z]+)",
            r"I'm ([A-Z][a-z]+ [A-Z][a-z]+)",
            r"My name is ([A-Z][a-z]+ [A-Z][a-z]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                data["name"] = match.group(1)
                break

        # Job title patterns
        title_patterns = [
            r"(?:I am|I'm) (?:a|an|the) ([A-Z][a-z\s]+) at",
            r"works as (?:a|an|the) ([A-Z][a-z\s]+)",
            r"role[:\s]+([A-Z][a-z\s]+)",
            r"position[:\s]+([A-Z][a-z\s]+)",
        ]
        common_titles = [
            "CEO", "CTO", "CFO", "COO", "CMO",
            "President", "Vice President", "VP",
            "Director", "Manager", "Lead",
            "Engineer", "Developer", "Designer",
            "Founder", "Co-Founder",
        ]

        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Validate it's a real title
                if any(t.lower() in title.lower() for t in common_titles):
                    data["title"] = title
                    break

        # Company patterns
        company_patterns = [
            r"(?:works at|working at) ([A-Z][a-zA-Z\s&]+)",
            r"(?:employed by|employee of) ([A-Z][a-zA-Z\s&]+)",
            r"at ([A-Z][a-zA-Z\s&]+) (?:since|as)",
        ]
        for pattern in company_patterns:
            match = re.search(pattern, content)
            if match:
                company = match.group(1).strip()
                # Remove trailing words like "as", "since"
                company = re.sub(r"\s+(as|since|in|for)$", "", company, flags=re.IGNORECASE)
                data["company"] = company
                break

        # Location patterns
        location_patterns = [
            r"based in ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
            r"lives in ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
            r"located in ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
        ]
        for pattern in location_patterns:
            match = re.search(pattern, content)
            if match:
                data["location"] = match.group(1)
                break

        # Education patterns
        education_patterns = [
            r"(?:graduated from|degree from|studied at) ([A-Z][a-zA-Z\s]+(?:University|College|Institute))",
            r"([A-Z][a-zA-Z\s]+(?:University|College|Institute)) (?:graduate|alumni)",
        ]
        for pattern in education_patterns:
            match = re.search(pattern, content)
            if match:
                data["education"] = match.group(1).strip()
                break

        # Social profiles
        social_profiles = {}

        # LinkedIn
        linkedin_patterns = [
            r"linkedin\.com/in/([a-zA-Z0-9\-]+)",
            r"linkedin\.com/profile/([a-zA-Z0-9\-]+)",
        ]
        for pattern in linkedin_patterns:
            match = re.search(pattern, content)
            if match:
                social_profiles["linkedin"] = f"https://linkedin.com/in/{match.group(1)}"
                break

        # Twitter/X
        twitter_patterns = [
            r"twitter\.com/([a-zA-Z0-9_]+)",
            r"x\.com/([a-zA-Z0-9_]+)",
            r"@([a-zA-Z0-9_]+)",
        ]
        for pattern in twitter_patterns:
            match = re.search(pattern, content)
            if match:
                username = match.group(1)
                social_profiles["twitter"] = f"https://twitter.com/{username}"
                break

        # GitHub
        github_patterns = [
            r"github\.com/([a-zA-Z0-9\-]+)",
        ]
        for pattern in github_patterns:
            match = re.search(pattern, content)
            if match:
                social_profiles["github"] = f"https://github.com/{match.group(1)}"
                break

        if social_profiles:
            data["social_profiles"] = social_profiles

        # Email
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(email_pattern, content)
        if match:
            data["email"] = match.group(0)

        # Phone (US format)
        phone_patterns = [
            r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            r"\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, content)
            if match:
                data["phone"] = match.group(0)
                break

        return data

    async def _extract_with_llm(self, content: str) -> Dict[str, Any]:
        """Extract person info using LLM."""
        # TODO: Integrate with Instructor + OpenAI/Anthropic
        return await self._extract_with_patterns(content)

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name",
                },
                "title": {
                    "type": "string",
                    "description": "Job title or role",
                },
                "company": {
                    "type": "string",
                    "description": "Current company",
                },
                "location": {
                    "type": "string",
                    "description": "Location/city",
                },
                "education": {
                    "type": "string",
                    "description": "Educational institution",
                },
                "social_profiles": {
                    "type": "object",
                    "description": "Social media profiles",
                    "properties": {
                        "linkedin": {"type": "string"},
                        "twitter": {"type": "string"},
                        "github": {"type": "string"},
                    },
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number",
                },
            },
        }


class PersonExperienceEnricher(EnrichmentPlugin):
    """
    Extract work experience and career history for a person.
    """

    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """Extract work experience."""
        result = EnrichmentResult(self.name)

        try:
            data = {}

            # Years of experience
            experience_patterns = [
                r"(\d+)\+?\s+years of experience",
                r"over (\d+) years",
                r"(\d+) years in",
            ]
            for pattern in experience_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    data["years_experience"] = match.group(1)
                    break

            # Skills extraction
            skill_keywords = [
                "python", "javascript", "java", "c++", "rust", "go",
                "machine learning", "ai", "deep learning",
                "react", "angular", "vue",
                "aws", "azure", "gcp", "cloud",
                "docker", "kubernetes",
                "sql", "nosql", "mongodb", "postgresql",
                "agile", "scrum", "devops",
            ]

            found_skills = []
            content_lower = content.lower()
            for skill in skill_keywords:
                if skill in content_lower:
                    found_skills.append(skill)

            if found_skills:
                data["skills"] = found_skills

            # Certifications
            cert_patterns = [
                r"certified ([A-Za-z\s]+(?:Developer|Engineer|Professional|Specialist))",
                r"certification[:\s]+([A-Za-z\s]+)",
            ]
            certifications = []
            for pattern in cert_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    cert = match.group(1).strip()
                    if cert not in certifications:
                        certifications.append(cert)

            if certifications:
                data["certifications"] = certifications

            result.data = data
            result.success = bool(data)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Experience enrichment failed: {e}")

        return result

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return {
            "type": "object",
            "properties": {
                "years_experience": {
                    "type": "string",
                    "description": "Years of professional experience",
                },
                "skills": {
                    "type": "array",
                    "description": "List of skills",
                    "items": {"type": "string"},
                },
                "certifications": {
                    "type": "array",
                    "description": "List of certifications",
                    "items": {"type": "string"},
                },
            },
        }
