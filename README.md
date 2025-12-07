# AutoOps Classroom

An AI-powered course recommendation platform with:
- FastAPI backend
- Streamlit frontend
- Resume-based skill extraction
- Personalized course recommendations
- Teacher course management

## Setup

```bash
# Create venv (optional)
pip install -r requirements.txt

# Initialize databases
python setupdb.py
```

## Run backend

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Run frontend

```bash
cd frontend
streamlit run app.py
```

Login with sample accounts:

- student1 / 123456 (role: student)
- teacher1 / 123456 (role: teacher)
