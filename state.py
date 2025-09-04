from pydantic import BaseModel, Field
from typing import TypedDict, Optional, Union

class InputState(BaseModel):
    input_message: str = Field(description="The response from the LLM")
    ai_response: str = Field(description="The response from the LLM", default="")

class PANDetailsState(TypedDict):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
    father_name: str = Field(description="The father's name of the user")
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")

##################################################
class PANVerificationState(BaseModel):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
    father_name: str = Field(description="The father's name of the user")
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")


class PANVerificationStateAck(BaseModel):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
    father_name: str = Field(description="The father's name of the user")
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")
##################################################

# class PANVerificationStateAck(TypedDict):
#     verification_status: str = Field(description="Status of PAN verification: success, failed, or error")
#     verification_message: str = Field(description="Verification result message")
#     verification_timestamp: str = Field(description="Timestamp when verification was performed")
 
class AadharDetailsState(TypedDict):
    aadhar_number: str = Field(description="The Aadhar card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
    name: str = Field(description="The name of the user")
    new_doc_needed: bool = Field(description="Whether a new document is needed for age proof")
    # THIS FIELD IS SUBJECT TO CHANGE BASED ON THE DOCUMENT TYPE PREFERENCE
    doc_type: str = Field(description="The type of document to uploaded")

class VoterIdDetailsState(TypedDict):
    name: str = Field(description="The name of the user")
    dob: str = Field(description="DD/MM/YYYY")
    voter_id: str = Field(description="The Voter ID of the user")
    new_doc_needed: bool = Field(description="Whether a new document is needed for age proof")
    doc_type: str = Field(description="The type of document to uploaded")


# class OverallState(TypedDict):
#     input_message: str = Field(description="The response from the LLM")
#     ai_response: str = Field(description="The response from the LLM")
#     pan_details: PANDetailsState = Field(description="The PAN card details of the user")
#     pan_verification_status: PANVerificationStateAck = Field(description="Status of PAN verification: success, failed, or error")
#     aadhar_details: AadharDetailsState = Field(description="The Aadhar card details of the user")
#     voterId_details: VoterIdDetailsState = Field(description="The Voter ID card details of the user")

class OverallState(TypedDict):
    input_message: str = Field(description="The response from the LLM")
    ai_response: str = Field(description="The response from the LLM")
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
    father_name: str = Field(description="The father's name of the user")
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")
    verification_status: str = Field(description="Status of PAN verification: success, failed, or error")
    verification_message: str = Field(description="Verification result message")
    verification_timestamp: str = Field(description="Timestamp when verification was performed")
 