# P&G AI Developer Interview Task: Structured Data Extraction

## Overview
This repository contains an end-to-end Python pipeline designed to extract structured promotion data from unstructured text using Google's Gemini API. 

The goal of this project is not just to parse text, but to build a highly defensible, resilient data pipeline that prioritizes type safety, gracefully handles LLM hallucinations, and mitigates prompt injection.

## Architecture & Approach
To build a production-ready pipeline, I implemented the following design decisions:
1. **Strict Validation:** Utilized `Pydantic V2` to act as a gatekeeper. It enforces strict schema adherence, handles type casting (e.g., parsing ISO 8601 dates), and actively rejects invalid schemas (`extra='forbid'`).
2. **Self-Healing LLM Loop:** Implemented a recursive retry mechanism. If the LLM returns invalid JSON or violates the Pydantic schema, the system catches the error and feeds it back to the LLM as a targeted prompt, allowing the model to self-correct up to a maximum of 3 retries.
3. **Observability:** Replaced standard `print()` statements with Python's built-in `logging` module to differentiate between INFO, WARNING (retries), and ERROR states, simulating a true production environment.
4. **Security Safeguards:** Used System Instructions to define the LLM's rigid persona and employed delimiters (`"""`) to separate instructions from the untrusted user input, effectively mitigating basic prompt injection attacks.

## Assumptions & Business Logic
* **Data Completeness:** The input text is assumed to contain the required fields. Because the pipeline uses strict Pydantic validation, missing mandatory fields will deliberately trigger a validation error rather than failing silently with `null` values.
* **Negative Constraints ("Convenience Stores"):** The text states the promotion applies to Tesco and Asda but excludes convenience stores. The schema was explicitly designed to capture this nuance via an `excluded_store_formats` field, preventing the business from accidentally applying discounts to ineligible store formats (e.g., Tesco Express).
* **Temporal Context:** Because the text mentions "April" without a year, the pipeline dynamically injects the current system year into the prompt rules to ensure the extracted ISO dates are accurate to the present day.

---

## Production & Scaling Considerations
While this pipeline is robust for a localized task, deploying this to a live enterprise environment would require addressing the following architectural challenges:

1. **The Synchronous Trap:** The current retry loop is synchronous. In a production API, LLM extraction should be asynchronous (using message queues like RabbitMQ/Celery) so the main application thread does not block or timeout during LLM generation.
2. **API Rate Limits:** To handle HTTP 429 (Too Many Requests) or 503 (Service Unavailable) errors from the LLM provider, an Exponential Backoff strategy (e.g., using the `tenacity` library) must be implemented around the network calls.
3. **Semantic Hallucinations:** Pydantic verifies that `discount_percentage` is an integer, but it cannot verify if it is the *correct* integer. A true production system requires a downstream deterministic grounding step (e.g., cross-checking the extracted brand against an internal P&G SQL database).
4. **Context Window Management:** For inputs significantly larger than a single paragraph (e.g., a 50-page PDF of retail guidelines), a chunking/map-reduce strategy is necessary to prevent the model from dropping information or exceeding token limits.
5. **Data Privacy (PII):** If input text is sourced from raw customer communications, a Data Loss Prevention (DLP) scrubber (like `spaCy` or offline regex) should redact PII before the payload is sent to any third-party LLM API.

---

## Future Improvements (With More Time)
* **Native Structured Outputs:** Instead of relying purely on prompt engineering and retry loops, I would utilize Gemini's native `response_schema` configuration, which enforces JSON output at the API level, drastically reducing token usage and retry rates.
* **Unit Testing:** Implement `pytest` to mock the Gemini API responses and test the Pydantic validation and retry logic in isolation without making live network calls.
* **CI/CD:** Add GitHub Actions to run formatting checks (`black`, `flake8`) and tests automatically on all pull requests.
