import os
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

from flask import (
    render_template, request,
    redirect, url_for, flash, session, jsonify
)
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from extensions import mongo

from . import member_bp


# --------------------------------------------------
# MEMBER AUTH CHECK
# --------------------------------------------------
def member_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "member":
            flash("Please login as a team member first.", "danger")
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated


# Colours for events
SHIFT_COLORS = {
    "A": "#0d6efd",
    "B": "#198754",
    "C": "#ffc107",
    "G": "#6f42c1",
}


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
@member_bp.route("/dashboard", endpoint="dashboard")
@member_required
def dashboard():
    user_id = ObjectId(session["user_id"])

    upcoming = list(
        mongo.db.shifts.find({"user_id": user_id}).sort("date", 1).limit(5)
    )

    projects_map = {str(p["_id"]): p["name"] for p in mongo.db.projects.find()}
    notifications = list(
        mongo.db.notifications.find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(5)
    )

    return render_template(
        "member/dashboard.html",
        upcoming=upcoming,
        projects_map=projects_map,
        notifications=notifications,
    )


# --------------------------------------------------
# MY SCHEDULE (PERSONAL + PROJECT TEAM VIEW)
# --------------------------------------------------
@member_bp.route("/my-schedule", endpoint="my_schedule")
@member_required
def my_schedule():
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}

    # Extract project IDs safely
    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except:
            pass

    # Load projects
    projects = []
    if project_ids:
        projects = list(
            mongo.db.projects.find({"_id": {"$in": project_ids}}).sort("name", 1)
        )

    # Convert IDs to string for HTML safety
    for p in projects:
        p["_id"] = str(p["_id"])

    selected_project = request.args.get("project_id")
    selected_pid_obj = None

    # validate selected project
    if selected_project:
        try:
            selected_pid_obj = ObjectId(selected_project)
        except:
            selected_pid_obj = None
            selected_project = None

        if selected_pid_obj not in project_ids:
            selected_pid_obj = None
            selected_project = None

    # default → first project
    if not selected_project and projects:
        selected_pid_obj = ObjectId(projects[0]["_id"])
        selected_project = projects[0]["_id"]

    # Build SAFE team list
    team_members_safe = []

    if selected_pid_obj:
        team_members = list(
            mongo.db.users.find({
                "role": "member",
                "project_ids": selected_pid_obj
            })
        )

        for u in team_members:
            team_members_safe.append({
                "_id": str(u["_id"]),
                "name": u.get("name", ""),
                "email": u.get("email", "")
            })

    # always a safe list
    if not team_members_safe:
        team_members_safe = []

    return render_template(
        "member/my_schedule.html",
        projects=projects,
        selected_project=selected_project,
        team_members=team_members_safe,
    )


# --------------------------------------------------
# API: MY SHIFTS (FULLCALENDAR)
# --------------------------------------------------
@member_bp.route("/api/my_shifts", endpoint="api_my_shifts")
@member_required
def api_my_shifts():
    user_id = ObjectId(session["user_id"])
    user = mongo.db.users.find_one({"_id": user_id}) or {}
    profile_pic = user.get("profile_picture", "default.png")
    
    shifts = list(mongo.db.shifts.find({"user_id": user_id}))

    events = []
    for s in shifts:
        date_str = s["date"]
        shift_code = s.get("shift_code", "")
        start_time = s.get("start_time") or "09:00"
        end_time = s.get("end_time") or "17:00"

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = f"{date_str}T{start_time}:00"

        if shift_code == "C":  # Night shift → next day
            end_date = date_obj + timedelta(days=1)
            end = f"{end_date.isoformat()}T{end_time}:00"
        else:
            end = f"{date_str}T{end_time}:00"

        project_name = ""
        pid = s.get("project_id")
        if pid:
            p = mongo.db.projects.find_one({"_id": pid})
            if p:
                project_name = p.get("name", "")

        task = s.get("task", "")
        title_parts = []
        if shift_code: title_parts.append(shift_code)
        if task: title_parts.append(task)
        if project_name: title_parts.append(f"[{project_name}]")

        title = " – ".join(title_parts) if title_parts else "Shift"

        events.append({
            "id": str(s["_id"]),
            "title": title,
            "start": start,
            "end": end,
            "backgroundColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "extendedProps": {
                "profile_pic": profile_pic,
                "user_id": str(user_id)
            }
        })

    return jsonify(events)


# --------------------------------------------------
# API: TEAM SHIFTS (PROJECT SPECIFIC)
# --------------------------------------------------
@member_bp.route("/api/team_shifts", endpoint="api_team_shifts")
@member_required
def api_team_shifts():
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}

    raw_pids = current_user.get("project_ids", [])
    allowed_projects = []
    for pid in raw_pids:
        try:
            allowed_projects.append(ObjectId(pid))
        except:
            pass

    query = {}

    uid = request.args.get("user_id")
    if uid:
        try:
            query["user_id"] = ObjectId(uid)
        except:
            return jsonify([])

    pid_param = request.args.get("project_id")
    if pid_param:
        try:
            pid_obj = ObjectId(pid_param)
        except:
            return jsonify([])

        if pid_obj not in allowed_projects:
            return jsonify([])

        query["project_id"] = pid_obj
    else:
        if allowed_projects:
            query["project_id"] = {"$in": allowed_projects}
        else:
            return jsonify([])

    shifts_cursor = mongo.db.shifts.find(query)
    users_list = list(mongo.db.users.find())
    users_map = {str(u["_id"]): {"name": u.get("name", "Unknown"), "profile_pic": u.get("profile_picture", "default.png")} for u in users_list}
    projects_map = {str(p["_id"]): p["name"] for p in mongo.db.projects.find()}

    events = []
    for s in shifts_cursor:
        date_str = s["date"]
        shift_code = s.get("shift_code", "")
        start_time = s.get("start_time") or "09:00"
        end_time = s.get("end_time") or "17:00"

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = f"{date_str}T{start_time}:00"

        if shift_code == "C":
            end_date = date_obj + timedelta(days=1)
            end = f"{end_date.isoformat()}T{end_time}:00"
        else:
            end = f"{date_str}T{end_time}:00"

        uid = str(s["user_id"])
        pid = str(s.get("project_id")) if s.get("project_id") else None

        user_info = users_map.get(uid, {"name": "Unknown", "profile_pic": "default.png"})
        user_name = user_info["name"]
        profile_pic = user_info["profile_pic"]
        project_name = projects_map.get(pid, "General") if pid else "General"
        task = s.get("task", "")

        tooltip = f"{user_name} • {project_name} • {shift_code} • {task}"

        events.append({
            "id": str(s["_id"]),
            "title": f"{project_name}: {user_name} – {shift_code}",
            "start": start,
            "end": end,
            "backgroundColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "extendedProps": {
                "tooltip": tooltip,
                "user_id": uid,
                "profile_pic": profile_pic,
                "user": user_name
            }
        })

    return jsonify(events)


# --------------------------------------------------
# REQUEST SHIFT CHANGE
# --------------------------------------------------
@member_bp.route("/request-change", methods=["GET", "POST"], endpoint="request_shift_change")
@member_required
def request_shift_change():
    user_id = ObjectId(session["user_id"])

    if request.method == "POST":
        mongo.db.shift_change_requests.insert_one({
            "user_id": user_id,
            "date": request.form.get("date"),
            "requested_shift": request.form.get("new_shift"),
            "reason": request.form.get("reason"),
            "status": "pending",
            "created_at": datetime.utcnow()
        })

        flash("Shift change request submitted!", "success")
        return redirect(url_for("member.dashboard"))

    from datetime import date
    today_date = date.today().isoformat()
    return render_template("member/request_shift_change.html", today_date=today_date)


# --------------------------------------------------
# REQUEST SWAP
# --------------------------------------------------
@member_bp.route("/request-swap", methods=["GET", "POST"], endpoint="request_swap")
@member_required
def request_swap():
    user_id = ObjectId(session["user_id"])
    users = list(mongo.db.users.find({"role": "member"}))

    if request.method == "POST":
        mongo.db.shift_swap_requests.insert_one({
            "requester_id": user_id,
            "target_user_id": ObjectId(request.form.get("target_user")),
            "date": request.form.get("date"),
            "reason": request.form.get("reason"),
            "status": "pending",
            "created_at": datetime.utcnow()
        })

        flash("Shift swap request submitted!", "success")
        return redirect(url_for("member.dashboard"))

    from datetime import date
    today_date = date.today().isoformat()
    return render_template("member/request_swap.html", users=users, today_date=today_date)


# --------------------------------------------------
# PROFILE (IMAGE UPLOAD)
# --------------------------------------------------
@member_bp.route("/profile", methods=["GET", "POST"], endpoint="profile")
@member_required
def profile():
    user_id = ObjectId(session["user_id"])
    user = mongo.db.users.find_one({"_id": user_id})
    
    if not user:
        flash("User not found.", "danger")
        return redirect("/member/dashboard")

    if request.method == "POST":
        file = request.files.get("profile_picture")

        if file and allowed_file(file.filename):
            filename = secure_filename(f"{user_id}.jpg")
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            mongo.db.users.update_one(
                {"_id": user_id},
                {"$set": {"profile_picture": filename}}
            )

            flash("Profile picture updated successfully!", "success")
            return redirect("/member/profile")

        flash("Invalid file type. Only JPG/PNG allowed.", "danger")

    profile_pic = user.get("profile_picture", "default.png") if user else "default.png"

    return render_template("member/profile.html", user=user, profile_pic=profile_pic)


# --------------------------------------------------
# TASK HANDOVER (SIMPLE TASK COMPLETED/TO DO SYSTEM)
# --------------------------------------------------
@member_bp.route("/task-handover", methods=["GET", "POST"], endpoint="task_handover")
@member_required
def task_handover():
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}
    
    # Get user's projects
    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except:
            pass
    
    projects = []
    if project_ids:
        projects = list(
            mongo.db.projects.find({"_id": {"$in": project_ids}}).sort("name", 1)
        )
        for p in projects:
            p["_id"] = str(p["_id"])
    
    selected_project = request.args.get("project_id") or ""
    selected_date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    
    # Get all task handovers for selected project and date
    task_entries = []
    users_map = {str(u["_id"]): u for u in mongo.db.users.find()}
    
    if selected_project:
        try:
            selected_pid_obj = ObjectId(selected_project)
            if selected_pid_obj in project_ids and selected_date:
                # Get all task entries for this project and date
                task_entries_raw = list(mongo.db.shift_logs.find({
                    "project_id": str(selected_pid_obj),
                    "date": selected_date
                }).sort("created_at", -1))
                
                for entry in task_entries_raw:
                    author_id = str(entry.get("user_id", ""))
                    author = users_map.get(author_id, {})
                    entry["author"] = author
                    task_entries.append(entry)
        except:
            pass
    
    # Default to first project if none selected
    if not selected_project and projects:
        selected_project = projects[0]["_id"]
    
    if request.method == "POST":
        project_id = request.form.get("project_id", "").strip()
        date = request.form.get("date", "").strip()
        shift_code = request.form.get("shift_code", "").strip()
        task_completed = request.form.get("task_completed", "").strip()
        task_to_do = request.form.get("task_to_do", "").strip()
        
        # Validate
        if not project_id:
            flash("Please select a project.", "warning")
            return redirect("/member/task-handover")
        
        if not date:
            flash("Please select a date.", "warning")
            return redirect("/member/task-handover")
        
        if not shift_code:
            flash("Please select a shift.", "warning")
            return redirect("/member/task-handover")
        
        if not task_completed and not task_to_do:
            flash("Please fill in at least one field (Task Completed or Task To Be Done).", "warning")
            return redirect("/member/task-handover")
        
        try:
            project_obj_id = ObjectId(project_id)
            if project_obj_id not in project_ids:
                flash("You don't have access to this project.", "danger")
                return redirect("/member/task-handover")
            
            # Create task entry
            task_entry = {
                "project_id": str(project_obj_id),
                "date": date,
                "shift_code": shift_code,
                "user_id": current_user_id,
                "works_completed": task_completed,
                "works_to_do": task_to_do,
                "created_at": datetime.utcnow()
            }
            mongo.db.shift_logs.insert_one(task_entry)
            flash("Task handover posted successfully! All team members can see it.", "success")
            return redirect(f"/member/task-handover?project_id={project_id}&date={date}")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect("/member/task-handover")
    
    return render_template(
        "member/task_handover.html",
        projects=projects,
        selected_project=selected_project,
        selected_date=selected_date,
        task_entries=task_entries
    )


# --------------------------------------------------
# VIEW SHIFT LOG (READ-ONLY FOR ALL MEMBERS)
# --------------------------------------------------
@member_bp.route("/view-shift-log", endpoint="view_shift_log")
@member_required
def view_shift_log():
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}
    
    # Get user's projects
    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except:
            pass
    
    projects = []
    if project_ids:
        projects = list(
            mongo.db.projects.find({"_id": {"$in": project_ids}}).sort("name", 1)
        )
    
    for p in projects:
        p["_id"] = str(p["_id"])
    
    selected_project = request.args.get("project_id") or ""
    selected_date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    
    selected_pid_obj = None
    if selected_project:
        try:
            selected_pid_obj = ObjectId(selected_project)
            if selected_pid_obj not in project_ids:
                selected_pid_obj = None
                selected_project = ""
        except:
            selected_pid_obj = None
            selected_project = ""
    
    if not selected_project and projects:
        selected_pid_obj = ObjectId(projects[0]["_id"])
        selected_project = projects[0]["_id"]
    
    # Ensure selected_project is always a string (not None)
    if selected_project is None:
        selected_project = ""
    
    log_entries = []
    if selected_pid_obj and selected_date:
        shifts = list(mongo.db.shifts.find({
            "project_id": selected_pid_obj,
            "date": selected_date
        }).sort("shift_code", 1))
        
        shift_ids = [str(s["_id"]) for s in shifts]
        log_entries_raw = list(mongo.db.shift_logs.find({
            "shift_id": {"$in": shift_ids}
        }).sort("created_at", -1))
        
        shifts_map = {str(s["_id"]): s for s in shifts}
        users_map = {str(u["_id"]): u for u in mongo.db.users.find()}
        
        for log in log_entries_raw:
            shift_id = log.get("shift_id")
            shift = shifts_map.get(shift_id) if shift_id else None
            if shift:
                user_id = str(shift.get("user_id"))
                user = users_map.get(user_id, {})
                log["shift"] = shift
                log["user"] = user
                log_entries.append(log)
    
    return render_template(
        "member/view_shift_log.html",
        projects=projects,
        selected_project=selected_project,
        selected_date=selected_date,
        log_entries=log_entries
    )
