from pydantic import BaseModel, Field
from typing import TypedDict, Optional, Union

class InputState(BaseModel):
    input_message: str = Field(description="The response from the LLM")
    ai_response: str = Field(description="The response from the LLM", default="")

class PANVerificationState(BaseModel):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
<<<<<<< HEAD
=======
    father_name: str = Field(description="The father's name of the user")
>>>>>>> 920f314 (AADHAR + PAN workflow)
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")

class PANVerificationStateAck(BaseModel):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
<<<<<<< HEAD
=======
    father_name: str = Field(description="The father's name of the user")
>>>>>>> 920f314 (AADHAR + PAN workflow)
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")

class OverallState(TypedDict):
    input_message: str = Field(description="The response from the LLM")
    ai_response: str = Field(description="The response from the LLM")
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
<<<<<<< HEAD
=======
    father_name: str = Field(description="The father's name of the user")
>>>>>>> 920f314 (AADHAR + PAN workflow)
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")
    verification_status: str = Field(description="Status of PAN verification: success, failed, or error")
    verification_message: str = Field(description="Verification result message")
    verification_timestamp: str = Field(description="Timestamp when verification was performed")
 