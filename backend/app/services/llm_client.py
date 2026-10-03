import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from app.config import settings
from app.schemas.ai import (
    RequirementExtractionResponse,
    RequirementMappingResponse,
    UnsupportedClaimResponse,
    ClarificationQuestionResponse,
    RequirementExtracted,
    RequirementMappingItem,
    UnsupportedClaimItem,
    ClarificationQuestionItem,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class BaseLLMClient(ABC):
    @abstractmethod
    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        pass

class MockLLMClient(BaseLLMClient):
    """Zero-dependency grounded deterministic mock client for offline tests and benchmarks."""

    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        if schema == RequirementExtractionResponse:
            return schema(
                requirements=[
                    RequirementExtracted(
                        id="REQ-001",
                        text="The lead applicant must be a UK-registered SME operating for at least 12 months.",
                        type="eligibility-related",
                        mandatory=True,
                        category="eligibility",
                        source_document="guideline",
                        source_page=1,
                        source_section="1. Eligibility Criteria",
                        source_excerpt="The lead applicant must be a UK-registered SME operating for at least 12 months."
                    ),
                    RequirementExtracted(
                        id="REQ-002",
                        text="Applications must include audited financial statements for the previous two financial years.",
                        type="mandatory",
                        mandatory=True,
                        category="financial",
                        source_document="guideline",
                        source_page=1,
                        source_section="2. Financial Documentation",
                        source_excerpt="Applications must include audited financial statements for the previous two financial years."
                    ),
                    RequirementExtracted(
                        id="REQ-003",
                        text="Projects must achieve minimum 40% reduction in carbon emissions verified by life-cycle analysis.",
                        type="mandatory",
                        mandatory=True,
                        category="project",
                        source_document="guideline",
                        source_page=2,
                        source_section="3. Technical Impact",
                        source_excerpt="Projects must achieve minimum 40% reduction in carbon emissions verified by life-cycle analysis."
                    ),
                    RequirementExtracted(
                        id="REQ-004",
                        text="Applicants should provide letters of support from at least two commercial pilot partners.",
                        type="recommendation",
                        mandatory=False,
                        category="recommendation",
                        source_document="guideline",
                        source_page=2,
                        source_section="4. Partner Validation",
                        source_excerpt="Applicants should provide letters of support from at least two commercial pilot partners."
                    ),
                ]
            )

        elif schema == RequirementMappingResponse:
            return schema(
                mappings=[
                    RequirementMappingItem(
                        requirement_id="REQ-001",
                        status="SUPPORTED",
                        evidence="EcoFilter Ltd is a UK-registered micro-SME (Companies House #09876543) incorporated in March 2023.",
                        source_document="application",
                        source_page=1,
                        source_section="Company Profile",
                        confidence=0.98,
                        reasoning="Applicant provides UK company registration number and date demonstrating 24+ months operation."
                    ),
                    RequirementMappingItem(
                        requirement_id="REQ-002",
                        status="MISSING",
                        evidence=None,
                        source_document="application",
                        source_page=None,
                        source_section=None,
                        confidence=0.95,
                        reasoning="Application draft mentions financial projections but contains no audited statements or balance sheets."
                    ),
                    RequirementMappingItem(
                        requirement_id="REQ-003",
                        status="WEAK",
                        evidence="Our pilot data indicates an estimated 35-45% decrease in plant greenhouse emissions.",
                        source_document="application",
                        source_page=2,
                        source_section="Environmental Impact",
                        confidence=0.82,
                        reasoning="Application claims 35-45% reduction but provides no formal third-party life-cycle analysis."
                    ),
                    RequirementMappingItem(
                        requirement_id="REQ-004",
                        status="SUPPORTED",
                        evidence="Two letters of intent are attached from Yorkshire Water and Northumbrian Water plc.",
                        source_document="application",
                        source_page=3,
                        source_section="Commercial Partners",
                        confidence=0.92,
                        reasoning="Letters of support from two distinct commercial utilities are explicitly referenced."
                    ),
                ]
            )

        elif schema == UnsupportedClaimResponse:
            return schema(
                claims=[
                    UnsupportedClaimItem(
                        claim="Our membrane technology reduces filtration energy consumption by 65% compared to all market alternatives.",
                        source_page=2,
                        reason="No comparative benchmark laboratory data or independent test reports are supplied.",
                        related_requirement="REQ-003",
                        status="No supporting evidence found in supplied materials"
                    )
                ]
            )

        elif schema == ClarificationQuestionResponse:
            return schema(
                questions=[
                    ClarificationQuestionItem(
                        requirement_id="REQ-002",
                        question="Please provide audited accounts or certified management accounts for FY2023-2024 and FY2024-2025.",
                        gap_type="MISSING",
                        suggested_evidence="Signed independent auditor statement or Companies House accounts."
                    ),
                    ClarificationQuestionItem(
                        requirement_id="REQ-003",
                        question="Can you supply the full life-cycle assessment (LCA) report verifying the minimum 40% emission reduction?",
                        gap_type="WEAK",
                        suggested_evidence="ISO 14040/44 compliant life cycle assessment report."
                    ),
                ]
            )

        raise ValueError(f"Mock client unsupported schema: {schema}")

class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        max_retries = settings.LLM_MAX_RETRIES
        delay = 1.0

        for attempt in range(max_retries):
            try:
                response = self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format=schema,
                    timeout=settings.LLM_TIMEOUT_SECONDS
                )
                parsed = response.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("OpenAI returned null structured output.")
                return parsed
            except Exception as e:
                logger.warning(f"OpenAI call attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"OpenAI LLM failure after {max_retries} attempts: {str(e)}")
                time.sleep(delay)
                delay *= 2.0

class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        max_retries = settings.LLM_MAX_RETRIES
        delay = 1.0

        full_prompt = f"{system_prompt}\n\nPlease respond strictly in valid JSON matching this schema:\n{prompt}"
        for attempt in range(max_retries):
            try:
                resp = self.model.generate_content(
                    full_prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                text = resp.text
                data = json.loads(text)
                return schema.model_validate(data)
            except Exception as e:
                logger.warning(f"Gemini call attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Gemini LLM failure after {max_retries} attempts: {str(e)}")
                time.sleep(delay)
                delay *= 2.0

def get_llm_client() -> BaseLLMClient:
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMClient(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    return MockLLMClient()
