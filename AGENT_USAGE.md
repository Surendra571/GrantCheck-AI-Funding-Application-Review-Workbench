# GrantCheck — Agent Usage & Pair-Programming Documentation

This document records the AI coding tools, representative prompts, delegated tasks, key agent mistakes identified and corrected, and verification protocols utilized in building the **GrantCheck — AI Funding Application Review Workbench**.

---

## 1. Tools Used

* **Google Antigravity (Advanced Agentic AI Assistant with Gemini 2.0 / Flash / Pro)**:
  * Used for end-to-end full-stack pair programming, codebase exploration, pipeline implementation, refactoring, and automated testing across frontend (React/TypeScript) and backend (FastAPI/SQLAlchemy).

---

## 2. Representative Prompts

The following prompts illustrate key milestones in developing the system:

### Prompt A: Architecture & Core Workflow Setup
> *"Build a web application called GrantCheck — AI Funding Application Review Workbench. The application reviews a draft funding application against a supplied grant/funding guideline. IMPORTANT PRODUCT RULE: This application is an AI-assisted completeness and evidence-review tool. It must NOT make an authoritative legal, regulatory, or funding-eligibility decision. Implement separate services: RequirementExtractor, RequirementMapper, EvidenceChecker, QuestionGenerator behind a service abstraction. Use strict Pydantic schemas for all AI responses. Deterministic scoring must be calculated by the backend, never by the LLM."*

### Prompt B: Controlled Multi-Step AI Pipeline & Anti-Hallucination
> *"Implement the AI workflow as a controlled 8-step pipeline: (1) parse guideline, (2) extract requirements, (3) parse application, (4) retrieve relevant application evidence, (5) map evidence to requirements, (6) detect weak/missing/ambiguous evidence, (7) detect unsupported application claims, (8) generate clarification questions. Every mapping must contain source evidence with page and section when available. If evidence cannot be found, return MISSING instead of guessing. For unsupported claims, never declare the claim false; state that no supporting evidence was found in supplied materials."*

### Prompt C: Human-in-the-Loop Review Workbench
> *"Implement the human-in-the-loop review workflow. Every AI-generated mapping must be reviewable with Confirm, Correct, and Reject actions. Confirm accepts the mapping and marks it complete; Correct allows changing status, evidence, and citation with required notes; Reject marks the requirement incomplete with required notes. Preserve original AI results and store human reviewer decisions separately. Recalculate deterministic checklist completion using reviewed states."*

### Prompt D: Document Versioning, Stale Detection & Re-analysis
> *"Implement robust document versioning and stale-assessment detection. Every document has an ID, version number, filename, SHA-256 hash, and upload timestamp. Never delete previous versions when a new version is uploaded. If content is unchanged, prevent duplicate version creation. If changed, create a new version and mark associated assessments as stale. The UI must display: 'Assessment is stale because a source document changed.' Provide a 'Re-analyze' action that creates a new assessment run while preserving the previous run for auditability."*

---

## 3. Delegated Work

The following development tasks were delegated to the AI coding agent:
1. **Pydantic v2 Schema Modeling**: Defining strict typing for requirements, mapping outputs, unsupported claims, clarification questions, and deterministic scoring models.
2. **Document Parsing Abstraction**: Extracting page-by-page text and headers from `.pdf` (PyMuPDF `fitz`), `.docx` (python-docx), and `.txt`/`.md` files, calculating SHA-256 hashes.
3. **Controlled 8-Step Pipeline**: Orchestrating guideline parsing $\to$ extraction $\to$ application parsing $\to$ candidate retrieval $\to$ mapping $\to$ citation verification $\to$ claim checking $\to$ question generation.
4. **Anti-Hallucination Layer (`CitationVerifier`)**: Programmatically verifying that AI-quoted excerpts exist verbatim within cited document pages; discarding or downgrading unverified citations to `MISSING`.
5. **Deterministic Scoring Engine (`ScoringService`)**: Pure Python calculation of completion percentage for mandatory requirements (`completed / total * 100`), ensuring recommendations remain separate and reviewer decisions override AI statuses.
6. **Versioning & Stale Engine (`VersioningService`)**: Content hashing, duplicate upload protection, version incrementing, stale state detection, and re-analysis run branching.
7. **FastAPI REST API Routes**: Implementing endpoints for assessments, document uploads, review submissions, supporting documents checklist, and summary reports.
8. **React + TypeScript Frontend**: Building the 5 required screens: New Assessment, Assessment Dashboard, Requirement Review Workbench modal, Supporting Documents Checklist, and Reviewed Completeness Summary Report with printable layout.
9. **Automated Pytest Suite**: Writing comprehensive unit and integration tests covering all critical paths.

---

## 4. Important Agent Mistakes & Rejected Suggestions

During development, several critical mistakes and sub-optimal suggestions were caught and resolved:

| Mistake / Sub-optimal Suggestion | Risk Identified | Correction Implemented |
|---|---|---|
| **LLM Score Estimation**: Early draft prompt allowed the LLM to output an `"overall_score": 82` field. | Violates the strict requirement that scoring must be deterministic and auditable. | Completely removed scoring from AI prompts. Implemented `ScoringService.calculate_score()` where completion is strictly calculated as `completed_mandatory / total_mandatory * 100`. |
| **Overwriting AI Data with Reviewer Edits**: Agent initially updated `ai_status` and `evidence` in-place when a reviewer submitted a correction. | Loss of historical AI audit trail; impossible to compare human judgment against AI recommendations. | Separated database columns into `ai_status` (immutable) and `reviewer_decision`, `reviewer_override_status`, `reviewer_notes`, `reviewed_at`. Derived `effective_status` dynamically. |
| **Claiming Unsupported Claims Were "False"**: Agent generated phrasing like *"Claim is false and unverified"*. | Violates product rule: workbench assists completeness review and must not make legal adjudications. | Enforced prompt and schema constraints: the system exclusively reports: *"No supporting evidence was found in the supplied materials."* |
| **Hallucinated Page Numbers & Citations**: Agent LLM occasionally generated plausible page numbers (e.g. page 12 of a 4-page document). | Reviewer misled by nonexistent citations. | Created deterministic `CitationVerifier` that checks if `source_page` exceeds `app_doc.page_count` or if quoted text is absent from the page, automatically downgrading the mapping to `MISSING`. |
| **Overwriting Historical Document Files on Disk**: Agent originally saved files using `storage_path = f"{doc_type}_{filename}"`. | Re-uploading a file with the same name erased previous version binaries. | Updated file naming schema to `{assessment_id}_{doc_type}_v{next_version}_{filename}`, ensuring historical document versions remain indefinitely preserved. |
| **Re-analysis Mutating In-Place**: Agent initially reset the existing assessment record upon re-analysis. | Erased previous reviewer notes and audit history. | Implemented run branching: `reanalyze_assessment` archives the existing run and creates a new assessment run (`parent_assessment_id = prev.id`, `run_number = prev.run_number + 1`), preserving the previous run for auditability. |
| **Windows Env Var Conflict (`DEBUG=release`)**: Pydantic crashed during app startup because host OS had `DEBUG=release`. | Server crashed on startup due to strict bool parsing error. | Added a custom Pydantic `@field_validator` in `config.py` that safely parses string variants or non-boolean environment inputs. |

---

## 5. Verification & Quality Assurance

To ensure system reliability, the implementation was verified across multiple dimensions:

1. **Automated Pytest Suite**:
   * **134+ tests passing** in `backend/tests/`:
     * `test_parser.py`: PDF, DOCX, TXT parsing, empty file validation, format errors, hash determinism.
     * `test_schemas.py`: Strict schema validation for requirements, mappings, claims, and questions.
     * `test_scoring.py`: Deterministic scoring rules, mandatory vs recommendation isolation, reviewer override matrix (confirm, correct, reject).
     * `test_versioning_and_stale.py`: Version numbers ($v_1 \to v_2$), unchanged document duplicate protection, stale triggers on guideline/application updates, multi-version preservation, and re-analysis audit runs.
     * `test_ai_services.py` & `test_pipeline_and_validation.py`: Anti-hallucination citation checks, gap-derived question generation, unsupported claim wording, retry handling.
     * `test_logging.py`: Structured event emission for all 12 core workflow events and sensitive data redaction.
     * `test_api_endpoints.py`: All REST API routes, input validation, and HTTP status codes (200, 201, 400, 404, 409, 413, 415, 422).
     * `test_e2e_workflow.py`: Complete lifecycle integration test from assessment creation through document replacement and re-analysis.

2. **Frontend Type-Checking & Production Build**:
   * Executed `npm run build` (`tsc && vite build`) with zero TypeScript errors or warnings.

3. **Security Audit**:
   * Verified zero hardcoded credentials, secret keys, or API tokens in the repository.
   * Redaction filters in structured logging to prevent accidental token or credential exposure.
   * File upload size limits (25MB) and format whitelist enforcement (`.pdf`, `.docx`, `.txt`, `.md`).

