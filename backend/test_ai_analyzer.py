import json
from ai_analyzer import analyze_resume_with_ai
# from google import genai
# load_dotenv()
resume_text='''  We are looking for a Python backend developer with experience in FastAPI, 
SQL databases, and resume/job description parsing. The role requires building APIs, analyzing text data,
 and providing recommendations for job seekers.
'''
jd_text=''' We are looking for a Python backend developer with experience in FastAPI, SQL databases, 
and resume/job description parsing. 
The role requires building APIs, analyzing text data, and providing recommendations for job seekers '''
result=analyze_resume_with_ai(resume_text,jd_text)
try:
    data=json.loads(result)
    print("match_score:",data["match_score"])
    print("matchedskills:",data["matched_skills"])
    print("missing_skills:",data["missing_score"])
    print("sugesstions:",data["sugesstions"])
    print("summary:",data["summary"])
except(json.JSONDecodeError,KeyError) as error:
    print("hey!,fix the json or column names")
    print("hey!,error is :",error)






