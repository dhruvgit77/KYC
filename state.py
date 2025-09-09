from pydantic import BaseModel, Field
<<<<<<< HEAD
from typing import TypedDict, Optional, Union
=======
from typing_extensions import TypedDict, Optional, Union
>>>>>>> 920f314 (AADHAR + PAN workflow)

class InputState(BaseModel):
    input_message: str = Field(description="The response from the LLM")
    ai_response: str = Field(description="The response from the LLM", default="")
<<<<<<< HEAD
=======
    human_response: str = Field(description="Acknowledgement from the user", default="")
>>>>>>> 920f314 (AADHAR + PAN workflow)

class PANDetailsState(TypedDict):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
<<<<<<< HEAD
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
 
=======
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")

class VerificationState(TypedDict):
    verification_status: str = Field(description="Status of PAN verification: success, failed, or error")
    verification_message: str = Field(description="Verification result message")
    verification_timestamp: str = Field(description="Timestamp when verification was performed")
    verification_doc: str = Field(description="The document which was used for verification")

>>>>>>> 920f314 (AADHAR + PAN workflow)
class AadharDetailsState(TypedDict):
    aadhar_number: str = Field(description="The Aadhar card number of the user")
    date_of_birth: str = Field(description="DD/MM/YYYY")
    name: str = Field(description="The name of the user")
    new_doc_needed: bool = Field(description="Whether a new document is needed for age proof")
<<<<<<< HEAD
    # THIS FIELD IS SUBJECT TO CHANGE BASED ON THE DOCUMENT TYPE PREFERENCE
    doc_type: str = Field(description="The type of document to uploaded")

=======
    
>>>>>>> 920f314 (AADHAR + PAN workflow)
class VoterIdDetailsState(TypedDict):
    name: str = Field(description="The name of the user")
    dob: str = Field(description="DD/MM/YYYY")
    voter_id: str = Field(description="The Voter ID of the user")
    new_doc_needed: bool = Field(description="Whether a new document is needed for age proof")
<<<<<<< HEAD
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
 
=======

class Form60DetailsState(TypedDict):
    agricultural_income: int = Field(description="Ask the user for his income with agricultural as source", default=0)
    other_income: int = Field(description="Ask if the user has any other source of income", default=0)
class OverallState(TypedDict):
    input_message: str = Field(description="The response from the LLM")
    ai_response: str = Field(description="The response from the LLM")
    human_response: str = Field(description="The response from the User for available document")
    OTP_verified: bool = Field(default=False)
    Form_60: Form60DetailsState = Field(description="Stores form60 details")
    pan_details: PANDetailsState = Field(description="The PAN card details of the user")
    pan_verification_status: VerificationState = Field(description="Status of PAN verification: success, failed, or error")
    aadhar_details: AadharDetailsState = Field(description="The Aadhar card details of the user")
    aadhar_verification_status: VerificationState = Field(description="Status of AADHAR verification: success, failed, or error")
    voterId_details: VoterIdDetailsState = Field(description="The Voter ID card details of the user")

class PANDetailsState_pydantic(BaseModel):
    pan_card_number: str = Field(description="The PAN card number of the user")
    date_of_birth: str = Field(description="Should be in DD/MM/YYYY format only. If the date can be converted it into DD/MM/YYYY, do that. Return NULL if not possible ")
    father_name: str = Field(description="The father's name of the user")
    pan_card_holders_name: str = Field(description="The name of the user as written on the PAN card")
>>>>>>> 920f314 (AADHAR + PAN workflow)
