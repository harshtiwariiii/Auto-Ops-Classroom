# AutoOps Classroom

An AI-powered course recommendation and learning management system built with FastAPI backend and Streamlit frontend.

## Features

### For Students
- **Resume-Based Skill Extraction**: Upload PDF or DOCX resumes to automatically extract skills
- **Personalized Recommendations**: Rate your skill levels and get AI-matched course recommendations using cosine similarity
- **Interactive Study Dashboard**: Track progress through courses, watch videos, take notes, and mark lessons complete
- **Progress Tracking**: Visual progress bars for modules and lessons

### For Teachers
- **Course Management**: Create and manage courses with detailed descriptions
- **Module & Lesson Creation**: Build structured learning paths with modules and lessons
- **Content Integration**: Add video URLs, notes, difficulty levels, and GitHub repository links
- **Course Editing**: Update course content, modules, and lessons

### Core Technology
- **AI Skill Matching**: Uses spaCy for name extraction and keyword-based skill detection
- **Recommendation Engine**: Cosine similarity algorithm for course matching
- **Secure Authentication**: JWT-based authentication with role-based access control
- **Database**: SQLite with separate databases for users and courses
- **Modern UI**: Dark-themed Streamlit interface with animated progress indicators

## Tech Stack

- **Backend**: FastAPI, Uvicorn, SQLite, spaCy, scikit-learn, pandas
- **Frontend**: Streamlit with custom CSS theming
- **Authentication**: Python-JOSE for JWT tokens
- **Document Processing**: pdfplumber, python-docx
- **Deployment**: Ready for Heroku (Procfile included)

## Database Schema

### Users Database (users.db)
- users: user_id, username, email, password_hash, role, full_name

### Courses Database (courses.db)
- courses: course_id, course_name, course_details
- course_skills: id, course_id, skill, weight
- modules: module_id, course_id, title, description, order_index
- lessons: lesson_id, module_id, title, video_url, notes, difficulty, order_index, github_url
- lesson_progress: user_id, lesson_id, completed, last_opened
- lesson_notes: user_id, lesson_id, notes, updated_at

## API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /login` - User login

### Student Features
- `POST /extract-skills/` - Extract skills from uploaded resume
- `POST /personalized-recommendations` - Get course recommendations
- `GET /courses/{course_id}/structure` - Get course structure with progress
- `POST /lessons/{lesson_id}/progress` - Update lesson completion
- `POST /lessons/{lesson_id}/notes` - Save lesson notes

### Teacher Features
- `POST /add-course` - Create new course
- `PUT /courses/{course_id}` - Update course
- `DELETE /courses/{course_id}/delete` - Delete course
- `POST /courses/{course_id}/add-module` - Add module to course
- `PUT /modules/{module_id}` - Update module
- `POST /modules/{module_id}/add-lesson` - Add lesson to module
- `PUT /lessons/{lesson_id}` - Update lesson
- `GET /courses` - List all courses
- `GET /courses/{course_id}/modules` - Get modules for course
- `GET /modules/{module_id}/lessons` - Get lessons for module

## Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AutoOps-Classroomhehe
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download spaCy model**
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Initialize database**
   ```bash
   python setupdb.py
   ```

## Running the Application

### Development Mode

1. **Start Backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Start Frontend** (in new terminal)
   ```bash
   cd frontend
   pip install -r requirements.txt
   streamlit run app.py
   ```

3. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

The application includes Procfile for Heroku deployment:

- Backend Procfile: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- Frontend Procfile: `web: streamlit run app.py --server.port $PORT --server.headless true`

## Sample Accounts

- **Student**: student1 / 123456
- **Teacher**: teacher1 / 123456

## Skill Extraction

The system extracts skills from resumes using:
- **Keyword Matching**: Predefined list of 100+ technical skills
- **Document Processing**: Supports PDF and DOCX formats
- **Name Extraction**: Uses spaCy NER for candidate name detection

Supported skill categories:
- Programming Languages (Python, Java, etc.)
- DevOps Tools (Docker, Kubernetes, etc.)
- Cloud Platforms (AWS, Azure, GCP)
- Data Engineering (SQL, Spark, etc.)
- Machine Learning (TensorFlow, PyTorch, etc.)
- Web Development (React, Node.js, etc.)
- And more...

## Recommendation Algorithm

1. Extract skills from resume upload
2. Student rates skill proficiency (1-10 scale)
3. System creates user skill vector
4. Compares with course skill vectors using cosine similarity
5. Returns ranked recommendations with match scores

## Security Features

- Password hashing with SHA-256
- JWT token authentication
- Role-based access control (student/teacher)
- Secure file upload handling
- CORS configuration for frontend-backend communication

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request



