import streamlit as st
import requests

# ------------------------------------------------------
# CONFIG
# ------------------------------------------------------
BACKEND = "http://127.0.0.1:8000"
st.set_page_config(page_title="AutoOps Classroom", layout="wide")

# ------------------------------------------------------
# GLOBAL DARK THEME (Netflix-style)
# ------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --bg-main: #020617;        /* almost black */
        --border-soft: #1f2937;
        --primary: #2563eb;
        --primary-soft: #1d4ed8;
        --primary-glow: rgba(37, 99, 235, 0.50);
        --text-main: #e5e7eb;
        --text-muted: #9ca3af;
    }

    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at top, #020617 0, #020617 45%, #020617 100%);
        color: var(--text-main);
    }

    [data-testid="stSidebar"] {
        background-color: #020617 !important;
        border-right: 1px solid var(--border-soft);
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1150px;
    }

    h1, h2, h3, h4 {
        color: var(--text-main);
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    p, span, div {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text-main);
    }

    /* Cards */
    .card {
        background: radial-gradient(circle at top left, #020617 0, #020617 45%, #020617 100%);
        padding: 1.2rem 1.4rem;
        border-radius: 16px;
        border: 1px solid #1f2937;
        box-shadow: 0 0 25px rgba(15, 23, 42, 0.70);
        margin-bottom: 1rem;
    }

    .card-header {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: var(--text-muted);
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #38bdf8);
        color: white;
        border-radius: 999px;
        padding: 0.45rem 1.4rem;
        border: none;
        font-weight: 600;
        box-shadow: 0 0 12px var(--primary-glow);
    }

    .stButton>button:hover {
        background: linear-gradient(90deg, #1d4ed8, #0ea5e9);
        box-shadow: 0 0 18px var(--primary-glow);
    }

    /* Progress bar (animated) */
    .match-progress-bg {
        width: 100%;
        height: 9px;
        border-radius: 999px;
        background: #020617;
        overflow: hidden;
        border: 1px solid #1f2937;
        margin-top: 0.35rem;
    }

    .match-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #22c55e, #a3e635, #facc15);
        width: 0;
        border-radius: inherit;
        box-shadow: 0 0 12px rgba(34, 197, 94, 0.6);
        animation: fill-anim 1s ease-out forwards;
    }

    @keyframes fill-anim {
        from { width: 0; }
        to   { width: var(--progress); }
    }

    .sidebar-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-main);
    }

    .sidebar-sub {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    hr.sidebar-divider {
        margin: 0.6rem 0 0.9rem 0;
        border: none;
        border-bottom: 1px solid #1f2937;
    }

    label {
        color: var(--text-main) !important;
    }

    .stTextInput>div>div>input,
    .stTextArea textarea {
        background-color: #020617 !important;
        color: var(--text-main) !important;
        border-radius: 0.75rem;
        border: 1px solid #1f2937;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------
# SESSION STATE INIT
# ------------------------------------------------------
st.session_state.setdefault("token", None)
st.session_state.setdefault("username", None)
st.session_state.setdefault("role", None)
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("open_lesson_video", None)
st.session_state.setdefault("open_lesson_notes", None)

# ------------------------------------------------------
# API WRAPPER
# ------------------------------------------------------
def api_request(method, endpoint, **kwargs):
    headers = kwargs.pop("headers", {})

    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    url = BACKEND + endpoint

    try:
        if method == "GET":
            return requests.get(url, headers=headers, **kwargs)
        elif method == "POST":
            return requests.post(url, headers=headers, **kwargs)
        elif method == "PUT":
            return requests.put(url, headers=headers, **kwargs)
        elif method == "DELETE":
            # DELETE usually does NOT require json or files
            return requests.delete(url, headers=headers)
    except Exception as e:
        st.error(f"Backend not reachable: {e}")
        return None

# ------------------------------------------------------
# AUTH UI
# ------------------------------------------------------
def login_ui():
    st.markdown(
        """
        <div class="card" style="margin-bottom: 1.3rem;">
            <div class="card-header">Welcome back</div>
            <h1 style="margin-top: 0.3rem;">Sign in to AutoOps Classroom</h1>
            <p style="color: var(--text-muted); max-width: 520px; margin-top: 0.4rem;">
                Continue learning with AI-powered course recommendations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        res = api_request("POST", "/login", json={"username": username, "password": password})

        if res is None:
            return

        if res.status_code == 200:
            data = res.json()
            st.session_state.token = data["access_token"]
            st.session_state.username = data["username"]
            st.session_state.role = data["role"]
            st.session_state.logged_in = True
            st.success("Login successful.")
            st.rerun()
        else:
            try:
                st.error(res.json().get("detail", "Login failed"))
            except:
                st.error("Unexpected server response.")

def register_ui():
    st.markdown(
        """
        <div class="card" style="margin-bottom: 1.3rem;">
            <div class="card-header">Create account</div>
            <h1 style="margin-top: 0.3rem;">Join AutoOps Classroom</h1>
            <p style="color: var(--text-muted); max-width: 520px; margin-top: 0.4rem;">
                Register as a student to get recommendations, or as a teacher to publish courses.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("register_form"):
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        full_name = st.text_input("Full Name", key="reg_fullname")
        role = st.selectbox("Role", ["student", "teacher"], key="reg_role")
        submitted = st.form_submit_button("Create account")

    if submitted:
        res = api_request(
            "POST",
            "/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "full_name": full_name,
                "role": role,
            },
        )

        if res is None:
            return

        if res.status_code == 200:
            data = res.json()
            st.session_state.token = data["access_token"]
            st.session_state.username = username
            st.session_state.role = role
            st.session_state.logged_in = True
            st.success("Registration successful.")
            st.rerun()
        else:
            try:
                st.error(res.json().get("detail", "Registration failed"))
            except:
                st.error("Unexpected server response.")

# ------------------------------------------------------
# STUDENT: RECOMMENDATIONS FLOW (UPLOAD RESUME)
# ------------------------------------------------------
def student_home():
    st.markdown(
        """
        <div class="card" style="margin-bottom: 1.6rem;">
            <div class="card-header">Student dashboard</div>
            <h1 style="margin-top: 0.3rem;">AI-powered course recommendations</h1>
            <p style="color: var(--text-muted); max-width: 660px; margin-top: 0.4rem;">
                Upload your resume, let the system extract your skills, rate them, and get
                the best-matching courses from your institution.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.25, 1])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="card-header">Step 1</div>
            <h3 style="margin-top: 0.3rem;">Upload your resume (PDF or DOCX)</h3>
            """,
            unsafe_allow_html=True,
        )

        file = st.file_uploader(
            "Upload resume",
            type=["pdf", "docx"],
            label_visibility="collapsed",
        )

        if file:
            st.success("File uploaded.")
            headers = {
                "Authorization": f"Bearer {st.session_state.token}",
                "accept": "application/json",
            }
            files = {"file": (file.name, file.getvalue(), "application/octet-stream")}

            res = requests.post(f"{BACKEND}/extract-skills/", headers=headers, files=files)

            if res.status_code == 200:
                data = res.json()
                name = data["name"]
                skills = data["skills"]

                if not skills:
                    st.warning("No skills detected. Try another resume.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    return

                st.markdown(
                    f"<p style='margin-top:0.6rem; color:var(--text-muted);'>Detected name: "
                    f"<strong>{name}</strong></p>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    """
                    <div class="card-header" style="margin-top: 1rem;">Step 2</div>
                    <h3 style="margin-top: 0.3rem;">Rate your skill levels</h3>
                    <p style="color:var(--text-muted); margin-top:0.2rem; font-size:0.85rem;">
                        Use the sliders to indicate how confident you feel about each detected skill.
                    </p>
                    """,
                    unsafe_allow_html=True,
                )

                skill_levels = {}
                for skill in skills:
                    skill_levels[skill] = st.slider(
                        skill.capitalize(), 1, 10, 5, key=f"skill_{skill}"
                    )

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Generate recommendations"):
                    rec = api_request(
                        "POST",
                        "/personalized-recommendations",
                        json={"skill_levels": skill_levels},
                    )

                    if rec and rec.status_code == 200:
                        with right:
                            show_recommendations(rec.json()["recommendations"])
                    else:
                        st.error("Failed to fetch recommendations.")
            else:
                try:
                    detail = res.json().get("detail", "Upload failed.")
                except Exception:
                    detail = "Upload failed: backend did not return JSON."
                st.error(f"Error from backend: {detail}")

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            """
            <div class="card">
                <div class="card-header">Recommendations</div>
                <h3 style="margin-top:0.3rem;">Your matches will appear here</h3>
                <p style="color:var(--text-muted); margin-top:0.4rem; font-size:0.9rem;">
                    Once you upload a resume and rate your skills, AI-ranked courses will show up here.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ------------------------------------------------------
# RECOMMENDATIONS UI (ANIMATED BARS + DETAILS)
# ------------------------------------------------------
def show_recommendations(recs):
    if not recs:
        st.info("No recommendations yet.")
        return

    st.markdown(
        """
        <div class="card">
            <div class="card-header">Recommended courses</div>
            <h2 style="margin-top: 0.3rem;">Best matches for your skill profile</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, course in enumerate(recs, start=1):
        score = int(course["score"] * 100)

        st.markdown(
            f"""
            <div class="card" style="margin-top: 0.9rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:0.7rem;">
                        <div style="
                            width: 36px;
                            height: 36px;
                            border-radius: 12px;
                            background: radial-gradient(circle at top, #1d4ed8 0, #0f172a 55%, #020617 100%);
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            font-size:18px;
                            box-shadow: 0 0 16px var(--primary-glow);
                        ">📘</div>
                        <div>
                            <h3 style="margin:0;">{course['course_name']}</h3>
                            <p style="margin:0.2rem 0 0; color:var(--text-muted); font-size:0.85rem;">
                                Ranked #{idx} • AI-matched based on your skill sliders
                            </p>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.8rem; color:var(--text-muted);">Match score</span><br />
                        <span style="font-weight:700; font-size:1.1rem;">{score}%</span>
                        <div class="match-progress-bg">
                            <div class="match-progress-fill" style="--progress: {score}%;"></div>
                        </div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("View details"):
            st.write(course.get("description", "Recommended based on your skills."))

        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------
# STUDENT: STUDY DASHBOARD (MODULES + LESSONS)
# ------------------------------------------------------
def student_study_dashboard():
    st.markdown(
        """
        <div class="card" style="margin-bottom: 1.4rem;">
            <div class="card-header">Study dashboard</div>
            <h1 style="margin-top: 0.3rem;">Your courses & learning path</h1>
            <p style="color:#9ca3af; max-width:650px; margin-top:0.4rem;">
                Explore each course step-by-step. Track progress, open lessons, and take
                notes while you watch lectures.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    res = api_request("GET", "/courses")
    if not res or res.status_code != 200:
        st.error("Could not load courses.")
        return

    courses = res.json()["courses"]
    if not courses:
        st.info("No courses available yet.")
        return

    course_names = [c["course_name"] for c in courses]
    selected_name = st.selectbox("Choose a course", course_names)
    course_id = next(c["course_id"] for c in courses if c["course_name"] == selected_name)

    st.markdown("<br>", unsafe_allow_html=True)

    struct_res = api_request("GET", f"/courses/{course_id}/structure")
    if not struct_res or struct_res.status_code != 200:
        st.error("Could not load course structure.")
        return

    modules = struct_res.json().get("modules", [])

    for module in modules:
        title = module["title"]
        desc = module["description"]
        total = module["total_lessons"]
        done = module["completed_lessons"]
        pct = module["progress_percent"]

        with st.expander(f"{title}   ({done}/{total} lessons completed)", expanded=False):
            st.markdown(
                f"""
                <div style="margin-bottom:0.4rem; color:#9ca3af;">{desc}</div>
                <div class="match-progress-bg" style="margin-top:0.1rem; margin-bottom:0.6rem;">
                    <div class="match-progress-fill" style="--progress: {pct}%;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # header row
            header_cols = st.columns([1, 4, 1, 1, 1.2, 1.2])
            with header_cols[0]:
                st.markdown("<span style='color:#9ca3af; font-size:0.8rem;'>Status</span>", unsafe_allow_html=True)
            with header_cols[1]:
                st.markdown("<span style='color:#9ca3af; font-size:0.8rem;'>Lesson</span>", unsafe_allow_html=True)
            with header_cols[2]:
                st.markdown("<span style='color:#9ca3af; font-size:0.8rem;'>Video</span>", unsafe_allow_html=True)
            with header_cols[3]:
                st.markdown("<span style='color:#9ca3af; font-size:0.8rem;'>Notes</span>", unsafe_allow_html=True)
            with header_cols[4]:
                st.markdown("<span style='color:#9ca3af; font-size:0.8rem;'>Difficulty</span>", unsafe_allow_html=True)
            with header_cols[5]:
                st.markdown("<span style='color:#9ca3af; font-size:0.8rem;'>GitHub</span>", unsafe_allow_html=True)


            for lesson in module["lessons"]:
                lid = lesson["lesson_id"]
                completed = lesson["completed"]
                cols = st.columns([1, 4, 1, 1, 1.2, 1.2])

                with cols[0]:
                    new_val = st.checkbox("", value=completed, key=f"lesson_done_{lid}")
                    if new_val != completed:
                        api_request(
                            "POST",
                            f"/lessons/{lid}/progress",
                            json={"completed": new_val},
                        )

                with cols[1]:
                    st.markdown(f"**{lesson['title']}**")

                with cols[2]:
                    if lesson["video_url"]:
                        if st.button("▶", key=f"vid_{lid}"):
                            st.session_state.open_lesson_video = lesson["video_url"]

                with cols[3]:
                    if st.button("📝", key=f"notes_{lid}"):
                        st.session_state.open_lesson_notes = lid

                with cols[4]:
                    st.markdown(f"<span style='color:#9ca3af;'>{lesson['difficulty']}</span>", unsafe_allow_html=True)
                
                with cols[5]:
                    if lesson.get("github_url"):
                        st.markdown(
                            f"<a href='{lesson['github_url']}' target='_blank' "
                            f"style='padding:4px 10px; background:#24292E; color:white; "
                            f"text-decoration:none; border-radius:4px; font-size:0.75rem;'>"
                            f"GitHub</a>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.write("-")
                

    # video section
    if st.session_state.open_lesson_video:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📺 Now watching")
        st.video(st.session_state.open_lesson_video)

    # notes section
    if st.session_state.open_lesson_notes:
        lid = st.session_state.open_lesson_notes
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📝 Your notes for this lesson")
        note_text = st.text_area("Write your notes here...", key=f"notes_text_{lid}")
        if st.button("Save notes", key=f"save_notes_{lid}"):
            api_request("POST", f"/lessons/{lid}/notes", json={"notes": note_text})
            st.success("Notes saved.")

# ------------------------------------------------------
# TEACHER: ADD COURSE
# ------------------------------------------------------
def teacher_add_course():
    st.markdown(
        """
        <div class="card" style="margin-bottom:1.5rem;">
            <div class="card-header">Teacher dashboard</div>
            <h1 style="margin-top:0.3rem;">Add a new course</h1>
            <p style="color:var(--text-muted); max-width:640px; margin-top:0.4rem;">
                Describe the course and its content. The system will automatically map
                its skills to students for better recommendations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("add_course_form"):
        name = st.text_input("Course title")
        details = st.text_area("Course description / outline", height=200)
        submitted = st.form_submit_button("Publish course")

    if submitted:
        res = api_request("POST", "/add-course", json={
            "course_name": name,
            "course_details": details
        })

        if res and res.status_code == 200:
            st.success("Course added successfully.")
        else:
            st.error("Could not add course.")

def teacher_delete_course():
    st.markdown("## 🗑 Delete a Course")

    res = api_request("GET", "/courses")
    if not res or res.status_code != 200:
        st.error("Could not load courses.")
        return

    courses = res.json().get("courses", [])
    if not courses:
        st.info("No courses available to delete.")
        return

    course_names = [c["course_name"] for c in courses]
    selected = st.selectbox("Select Course to Delete", course_names)

    course_id = next(c["course_id"] for c in courses if c["course_name"] == selected)

    st.warning(
        f"""
        ⚠ **Are you sure? Deleting `{selected}` will remove:**
        - All modules inside the course  
        - All lessons inside those modules  
        - All student progress  
        - **This action cannot be undone**
        """
    )

    if st.button("DELETE COURSE"):
        res = api_request(
            "DELETE",
            f"/courses/{course_id}/delete"
        )

        if res is None:
            st.error("❌ Backend not reachable or request failed.")
        elif res.status_code == 200:
            st.success("Course deleted successfully!")
        else:
            st.error(f"Error: {res.text}")


# ------------------------------------------------------
# TEACHER: VIEW COURSES
# ------------------------------------------------------
def teacher_view_courses():
    st.markdown(
        """
        <div class="card" style="margin-bottom:1.2rem;">
            <div class="card-header">Teacher dashboard</div>
            <h1 style="margin-top:0.3rem;">All published courses</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    res = api_request("GET", "/courses")

    if res and res.status_code == 200:
        courses = res.json()["courses"]
        if not courses:
            st.info("No courses added yet.")
            return

        for c in courses:
            st.markdown(
                f"""
                <div class="card" style="margin-top:0.7rem;">
                    <h3 style="margin-bottom:0.3rem;">{c['course_name']}</h3>
                    <p style="color:var(--text-muted); margin-top:0;">
                        {c['course_details'] or 'No description provided.'}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.error("Failed to load courses.")

# ------------------------------------------------------
# TEACHER: ADD MODULES
# ------------------------------------------------------
def teacher_add_module():
    st.markdown(
        """
        <div class="card" style="margin-bottom:1.2rem;">
            <div class="card-header">Teacher dashboard</div>
            <h1 style="margin-top:0.3rem;">Add module to a course</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    courses_res = api_request("GET", "/courses")
    if not courses_res or courses_res.status_code != 200:
        st.error("Could not load courses.")
        return

    courses = courses_res.json()["courses"]
    if not courses:
        st.warning("Add a course first.")
        return

    course_names = [c["course_name"] for c in courses]
    selected = st.selectbox("Select Course", course_names)

    course_id = next(c["course_id"] for c in courses if c["course_name"] == selected)

    st.write("### Module Details")
    title = st.text_input("Module Title")
    desc = st.text_area("Module Description")

    if st.button("Add Module"):
        res = api_request(
            "POST",
            f"/courses/{course_id}/add-module",
            json={"title": title, "description": desc},
        )
        if res and res.status_code == 200:
            st.success("Module added successfully!")
        else:
            st.error("Failed to add module.")



# ------------------------------------------------------
# TEACHER: ADD LESSONS
# ------------------------------------------------------
def teacher_add_lesson():
    st.markdown(
        """
        <div class="card" style="margin-bottom:1.2rem;">
            <div class="card-header">Teacher dashboard</div>
            <h1 style="margin-top:0.3rem;">Add lesson to a module</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    courses_res = api_request("GET", "/courses")
    if not courses_res or courses_res.status_code != 200:
        st.error("Could not load courses.")
        return

    courses = courses_res.json()["courses"]
    if not courses:
        st.warning("Add a course first.")
        return

    course_names = [c["course_name"] for c in courses]
    selected_course = st.selectbox("Select Course", course_names)

    course_id = next(c["course_id"] for c in courses if c["course_name"] == selected_course)

    modules_res = api_request("GET", f"/courses/{course_id}/modules")
    if not modules_res or modules_res.status_code != 200:
        st.error("Could not load modules.")
        return

    modules = modules_res.json()["modules"]
    if not modules:
        st.warning("No modules yet. Add one first.")
        return

    module_titles = [m["title"] for m in modules]
    selected_module = st.selectbox("Select Module", module_titles)

    module_id = next(m["module_id"] for m in modules if m["title"] == selected_module)

    st.write("### Lesson Details")
    title = st.text_input("Lesson Title")
    video_url = st.text_input("Video URL (YouTube)")
    notes = st.text_area("Lesson Notes")
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    github_url = st.text_input("GitHub Repository Link (optional)")


    if st.button("Add Lesson"):
        res = api_request(
            "POST",
            f"/modules/{module_id}/add-lesson",
            json={
                "title": title,
                "video_url": video_url,
                "notes": notes,
                "difficulty": difficulty,
                "github_url": github_url,
            },
        )
        if res and res.status_code == 200:
            st.success("Lesson added successfully!")
        else:
            st.error("Failed to add lesson.")

# ------------------------------------------------------
# MAIN ROUTING
# ------------------------------------------------------
st.sidebar.markdown(
    """
    <div class="sidebar-title">AutoOps Classroom</div>
    <div class="sidebar-sub">AI-guided course mapping</div>
    <hr class="sidebar-divider" />
    """,
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Sign in", "Create account"])
    with tab1:
        login_ui()
    with tab2:
        register_ui()
    st.stop()

st.sidebar.success(
    f"Logged in as {st.session_state.username} ({st.session_state.role})"
)

if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.logged_in = False
    st.rerun()

if st.session_state.role == "student":
    student_menu = st.sidebar.radio(
        "Student menu",
        ["Recommendations", "Study dashboard"],
    )
    if student_menu == "Recommendations":
        student_home()
    else:
        student_study_dashboard()

elif st.session_state.role == "teacher":
    menu = st.sidebar.radio(
        "Teacher menu",
        ["Add course", "Manage modules", "Manage lessons", "View courses", "Delete course"],
    )
    if menu == "Add course":
        teacher_add_course()
    elif menu == "Manage modules":
        teacher_add_module()
    elif menu == "Manage lessons":
        teacher_add_lesson()
    elif menu == "View courses":
        teacher_view_courses()
    elif menu == "Delete course":
        teacher_delete_course()
