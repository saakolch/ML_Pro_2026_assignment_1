from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Features(BaseModel):
    model_config = ConfigDict(extra='forbid')

    Department: Literal["Business Administration", "Computer Science and Engineering", "Economics", "Electrical and Electronic Engineering", "English", "Journalism, Communication and Media Studies", "Law and Human Rights", "Political Science", "Public Health", "Sociology"]
    Gender: Literal["Male", "Female"]
    HSC: float = Field(..., ge=2.17, le=5.0)
    SSC: float = Field(..., ge=3.0, le=5.0)
    Income: Literal["Low (Below 15,000)", "Upper middle (30,000-50,000)", "Lower middle (15,000-30,000)", "High (Above 50,000)", "Low (Below 15,000) ", "Lower middle (15,000-30,000) ", "High (Above 50,000) ", "Lower middle (15,000-30,000)  ", "High (Above 50,000)  ", "Upper middle (30,000-50,000) "]
    Hometown: Literal["Village", "City"]
    Computer: Literal[1, 2, 3, 4, 5]
    Preparation: Literal["More than 3 Hours", "0-1 Hour", "2-3 Hours"]
    Gaming: Literal["0-1 Hour", "More than 3 Hours", "2-3 Hours"]
    Attendance: Literal["80%-100%", "Below 40%", "60%-79%", "40%-59%"]
    Job: Literal["No", "Yes"]
    English: Literal[1, 2, 3, 4, 5]
    Extra: Literal["Yes", "No"]
    Semester: Literal["6th", "7th", "3rd", "4th", "2nd", "11th", "5th", "9th", "8th", "10th", "12th"]
    Last: float = Field(..., ge=1.0, le=4.0)


