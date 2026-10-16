#main.py                                                                                                      
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field,field_validator
from database import get_connection
from analyzer import analyze_resume
import json
from fastapi.middleware.cors import CORSMiddleware
import logging  
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],     allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# allow_origions=
# ["http://127.0.0.1:8000/api/analyze",
# "http://127.0.0.1:5500/api/analyze",
# "http://localhost:5500/api/analyze",
# "http://127.0.0.1:5501/api/analyze",
# "http://localhost:8000/api/analyze",
# "http://127.0.0.1:8000/api/analyze"],
# allow_credentials=False,
# allow_methods=["GET","POST"],allow_headers=["content-type"])

class AnalyzeRequest(BaseModel):
    resume_text: str=Field(min_length=50)
    jd_text: str=Field(min_length=50)
    @field_validator("resume_text","jd_text")
    @classmethod
    def not_blank_validate(cls,values):
        if not values.strip():
            raise ValueError("fill without spaces")
        return values


@app.get("/")
def home():
    return {
        "message": "Resume Analyzer Backend is Running"
    }


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    result = analyze_resume(request.resume_text,request.jd_text)
    print(result)
    connection = None
    cursor = None
    analysis_id = None

    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            INSERT INTO resume_analyzer (resume_text, jd_text, match_score, matched_skills, missing_skills,sugesstions)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query, (
                request.resume_text,
                request.jd_text,
                result["match_score"],
                json.dumps(result["matched_skills"]),
                json.dumps(result["missing_skills"]),
                # result["match_score"],
                json.dumps(result["sugesstions"])
            )
        )

        connection.commit()
        analysis_id = cursor.lastrowid

        
        
    except Exception as error:
        if connection is not None and connection.is_connected():
            connection.rollback()  
        logger.exception("failed to save resume analysis")
        raise HTTPException(
            status_code=500,
            detail="Failed to save analysis"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
    return {
        "Analysis_Id": analysis_id,
        **result
    }

# Backend API: Retrieve analysis history
@app.get("/api/analyses")
def get_analyses():
    connection = None
    cursor = None

    try:
        # Connect to MySQL
        connection = get_connection()

        # Create a cursor that returns dictionary rows
        cursor = connection.cursor(dictionary=True)

        # Fetch the latest 20 analyses
        query = """SELECT
                analysis_id,
                match_score,
                matched_skills,
                missing_skills,
                created_At,
                sugesstions
            FROM resume_analyzer
            ORDER BY analysis_id DESC
            LIMIT 20"""

        cursor.execute(query)
        analyses = cursor.fetchall()

        for analysis in analyses:
            for field in ("matched_skills", "missing_skills"):
                value = analysis[field]

                if isinstance(value, str):
                    analysis[field] = json.loads(value)

        return {"analyses": analyses}

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analyses"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
