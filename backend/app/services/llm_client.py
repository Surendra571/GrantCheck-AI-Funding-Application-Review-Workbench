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
        import re

        if schema == RequirementExtractionResponse:
            # 1. Check for explicit REQ/REC tags in the prompt text
            req_rec_pattern = re.compile(
                r'(REQ-\d+|REC-\d+)[^\w\n]*([^\n\r]+(?:\n(?![A-Z0-9\n\r\t]+[—\-\:\.]|\d+\.)[^\n\r]+)?)',
                re.IGNORECASE
            )
            matches = list(req_rec_pattern.finditer(prompt))
            if matches:
                reqs = []
                for m in matches:
                    req_id = m.group(1).upper()
                    content = m.group(2).strip()
                    content = re.sub(r'^[—\-:\s]+', '', content).strip()
                    is_rec = req_id.startswith("REC") or "encourage" in content.lower() or "recommend" in content.lower()
                    req_type = (
                        "recommendation" if is_rec
                        else ("eligibility-related" if "eligib" in content.lower()
                        else ("submission-related" if any(w in content.lower() for w in ["timeline", "submission", "plan", "milestone"])
                        else "mandatory"))
                    )
                    cat = (
                        "recommendation" if is_rec
                        else ("eligibility" if "eligib" in content.lower()
                        else ("financial" if any(w in content.lower() for w in ["budget", "inr", "cost", "financial", "audit"])
                        else ("project" if any(w in content.lower() for w in ["scope", "environmental", "emission", "energy"])
                        else "submission")))
                    )
                    reqs.append(
                        RequirementExtracted(
                            id=req_id,
                            text=content,
                            type=req_type,
                            mandatory=not is_rec,
                            category=cat,
                            source_document="guideline",
                            source_page=1,
                            source_section="Mandatory Eligibility Requirements" if not is_rec else "Recommended Information",
                            source_excerpt=content,
                        )
                    )
                return schema(requirements=reqs)

            # 2. Check for CleanTech Horizon guideline text
            if "cleantech" in prompt.lower() or "fewer than 250 employees" in prompt.lower() or "ecofilter" in prompt.lower():
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
                            text="Projects must achieve a minimum 40% reduction in carbon emissions verified by life-cycle analysis.",
                            type="mandatory",
                            mandatory=True,
                            category="project",
                            source_document="guideline",
                            source_page=1,
                            source_section="3. Technical & Environmental Impact",
                            source_excerpt="Projects must achieve a minimum 40% reduction in carbon emissions verified by life-cycle analysis."
                        ),
                        RequirementExtracted(
                            id="REQ-004",
                            text="Applicants should provide letters of support from at least two commercial pilot partners.",
                            type="recommendation",
                            mandatory=False,
                            category="recommendation",
                            source_document="guideline",
                            source_page=1,
                            source_section="4. Commercial Partner Validation",
                            source_excerpt="Applicants should provide letters of support from at least two commercial pilot partners."
                        ),
                        RequirementExtracted(
                            id="REQ-005",
                            text="A full risk assessment matrix identifying at least five technological and market risks with mitigation protocols must be included in Section D of the proposal narrative.",
                            type="mandatory",
                            mandatory=True,
                            category="submission",
                            source_document="guideline",
                            source_page=1,
                            source_section="5. Risk Assessment & Governance",
                            source_excerpt="A full risk assessment matrix identifying at least five technological and market risks with mitigation protocols must be included in Section D of the proposal narrative."
                        ),
                    ]
                )

            # 3. Dynamic generic extraction for arbitrary numbered/bulleted/labelled guidelines
            num_pattern = re.compile(
                r'(?:^|\n)\s*(?:(\d+)[\.\)]|[•\-\*]|(?:Eligibility|Requirement|Criteria|Mandatory|Recommendation):?)\s*([^\n\r]+(?:must|shall|required|eligible|eligibility|should|recommend)[^\n\r]+)',
                re.IGNORECASE,
            )
            num_matches = list(num_pattern.finditer(prompt))
            if num_matches:
                reqs = []
                for idx, m in enumerate(num_matches, 1):
                    content = m.group(2).strip()
                    is_rec = "recommend" in content.lower() or "encourage" in content.lower() or "should" in content.lower()
                    reqs.append(
                        RequirementExtracted(
                            id=f"REQ-{idx:03d}",
                            text=content,
                            type="recommendation" if is_rec else "mandatory",
                            mandatory=not is_rec,
                            category="eligibility" if "eligib" in content.lower() else "project",
                            source_document="guideline",
                            source_page=1,
                            source_section="Guideline Requirements",
                            source_excerpt=content,
                        )
                    )
                if reqs:
                    return schema(requirements=reqs)

            # If no requirements can be extracted, return empty list (triggers zero-requirement failure handler)
            return schema(requirements=[])

        elif schema == RequirementMappingResponse:
            # 1. EcoSpark / Green Innovation Micro-Grant application
            if "ecospark" in prompt.lower() or "hyderabad" in prompt.lower() or "solar-powered" in prompt.lower() or "450,000" in prompt.lower():
                return schema(
                    mappings=[
                        RequirementMappingItem(
                            requirement_id="REQ-001",
                            status="SUPPORTED",
                            evidence="Organization: EcoSpark Community Solutions Pvt. Ltd.\nLocation: Hyderabad, Telangana, India\nOrganization type: Private limited company\nYears operating: 3 years",
                            source_document="application",
                            source_page=1,
                            source_section="Applicant Information",
                            confidence=0.98,
                            reasoning="Application draft specifies 3 years of operating history as a private limited company in Hyderabad, India, satisfying the 2-year eligibility requirement."
                        ),
                        RequirementMappingItem(
                            requirement_id="REQ-002",
                            status="SUPPORTED",
                            evidence="We expect the project to reduce electricity consumption by approximately 20% and reduce annual carbon emissions by approximately 12 tonnes.",
                            source_document="application",
                            source_page=1,
                            source_section="Environmental Benefit",
                            confidence=0.90,
                            reasoning="Application details expected 20% electricity reduction and 12 tonnes annual carbon reduction."
                        ),
                        RequirementMappingItem(
                            requirement_id="REQ-003",
                            status="WEAK",
                            evidence="Budget\nSolar equipment: INR 280,000\nCooling equipment: INR 120,000\nInstallation: INR 50,000\nTotal: INR 450,000",
                            source_document="application",
                            source_page=1,
                            source_section="Budget",
                            confidence=0.82,
                            reasoning="Requested funding of INR 450,000 is under the INR 500,000 cap, but the detailed project budget attachment is acknowledged as omitted in the draft."
                        ),
                        RequirementMappingItem(
                            requirement_id="REQ-004",
                            status="SUPPORTED",
                            evidence="Implementation Plan\nMonth 1: finalize site and equipment selection.\nMonth 2: procure equipment and complete installation.\nMonth 3: commission the system and begin monitoring.",
                            source_document="application",
                            source_page=1,
                            source_section="Implementation Plan",
                            confidence=0.94,
                            reasoning="A 3-month implementation timeline with specific monthly activity milestones and commissioning date is provided."
                        ),
                        RequirementMappingItem(
                            requirement_id="REC-001",
                            status="MISSING",
                            evidence=None,
                            source_document="application",
                            source_page=None,
                            source_section=None,
                            confidence=0.95,
                            reasoning="No baseline environmental data from the 12 months preceding the project was found in the application materials."
                        ),
                        RequirementMappingItem(
                            requirement_id="REC-002",
                            status="WEAK",
                            evidence="commission the system and begin monitoring.",
                            source_document="application",
                            source_page=1,
                            source_section="Implementation Plan",
                            confidence=0.75,
                            reasoning="Application notes monitoring will begin in Month 3 but does not detail the formal measurement framework, instruments, or verification metrics."
                        ),
                    ]
                )

            # 2. EcoFilter / CleanTech Horizon application
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
                        source_page=1,
                        source_section="Environmental Impact",
                        confidence=0.82,
                        reasoning="Application claims 35-45% reduction but provides no formal third-party life-cycle analysis."
                    ),
                    RequirementMappingItem(
                        requirement_id="REQ-004",
                        status="SUPPORTED",
                        evidence="Two letters of intent are attached from Yorkshire Water and Northumbrian Water plc.",
                        source_document="application",
                        source_page=1,
                        source_section="Commercial Partners",
                        confidence=0.92,
                        reasoning="Letters of support from two distinct commercial utilities are explicitly referenced."
                    ),
                    RequirementMappingItem(
                        requirement_id="REQ-005",
                        status="MISSING",
                        evidence=None,
                        source_document="application",
                        source_page=None,
                        source_section=None,
                        confidence=0.90,
                        reasoning="Proposal narrative does not include Section D risk assessment matrix with required mitigation protocols."
                    ),
                ]
            )

        elif schema == UnsupportedClaimResponse:
            if "ecospark" in prompt.lower() or "hyderabad" in prompt.lower() or "20 similar" in prompt.lower():
                return schema(
                    claims=[
                        UnsupportedClaimItem(
                            claim="EcoSpark has successfully completed more than 20 similar sustainability projects for local institutions.",
                            source_page=1,
                            reason="No client references, completion certificates, or project portfolio are supplied to substantiate the claim of 20+ completed projects.",
                            related_requirement="REQ-001",
                            status="No supporting evidence found in supplied materials"
                        )
                    ]
                )

            return schema(
                claims=[
                    UnsupportedClaimItem(
                        claim="Our membrane technology reduces filtration energy consumption by 65% compared to all market alternatives.",
                        source_page=1,
                        reason="No comparative benchmark laboratory data or independent test reports are supplied.",
                        related_requirement="REQ-003",
                        status="No supporting evidence found in supplied materials"
                    )
                ]
            )

        elif schema == ClarificationQuestionResponse:
            if "ecospark" in prompt.lower() or "hyderabad" in prompt.lower() or "rec-001" in prompt.lower():
                return schema(
                    questions=[
                        ClarificationQuestionItem(
                            requirement_id="REQ-003",
                            question="Please provide the itemized budget breakdown attachment and vendor quotations required by the funding guideline.",
                            gap_type="WEAK",
                            suggested_evidence="Itemized supplier quotation and detailed budget schedule."
                        ),
                        ClarificationQuestionItem(
                            requirement_id="REC-001",
                            question="Can you supply baseline utility electricity bills or measured energy consumption logs for the facility over the past 12 months?",
                            gap_type="MISSING",
                            suggested_evidence="12 months of electricity bills or third-party energy audit report."
                        ),
                    ]
                )

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
                logger.warning(
                    "OpenAI call attempt %s/%s failed (%s)",
                    attempt + 1,
                    max_retries,
                    type(e).__name__,
                )
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"OpenAI LLM failure after {max_retries} attempts."
                    ) from None
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
                logger.warning(
                    "Gemini call attempt %s/%s failed (%s)",
                    attempt + 1,
                    max_retries,
                    type(e).__name__,
                )
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Gemini LLM failure after {max_retries} attempts."
                    ) from None
                time.sleep(delay)
                delay *= 2.0

def get_llm_client() -> BaseLLMClient:
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be configured.")
        return OpenAILLMClient(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=gemini requires GEMINI_API_KEY to be configured.")
        return GeminiLLMClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    if provider == "mock":
        return MockLLMClient()
    raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'. Expected mock, openai, or gemini.")
