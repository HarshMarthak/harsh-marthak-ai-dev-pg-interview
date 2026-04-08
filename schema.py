from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List
from datetime import date

class PromotionSchema(BaseModel):
    # Forbidding extra fields to prevent LLM hallucinations or prompt injection leakage
    model_config = ConfigDict(extra='forbid')

    product_name: str = Field(description="Full name of the product")
    brand: str = Field(description="The brand owner of the product")
    discount_percentage: int = Field(description="The discount value as an integer")
    promotion_start_date: date = Field(description="Start date in YYYY-MM-DD")
    promotion_end_date: date = Field(description="End date in YYYY-MM-DD")
    eligible_retailers: List[str] = Field(description="List of retailers participating")
    
    # Added to capture business exclusions (e.g., convenience stores)
    excluded_store_formats: List[str] = Field(
        default=[], 
        description="List of store types or formats excluded from the promotion"
    )

    @field_validator('discount_percentage')
    @classmethod
    def validate_discount(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Discount must be between 0 and 100")
        return v