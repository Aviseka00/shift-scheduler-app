import os
import io
from datetime import datetime, timedelta, date

from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from flask import (
    render_template, request,
    redirect, url_for, flash, session,
    jsonify, Response, current_app
)

from extensions import mongo
from . import member_bp


# --------------------------------------------------
# FILE UPLOAD HELPER
# --------------------------------------------------
def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


# --------------------------------------------------
# PDF LIB CHECK
# --------------------------------------------------
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# --------------------------------------------------
# MEMBER LOGIN CHECK
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


# --------------------------------------------------
# SHIFT COLORS
# --------------------------------------------------
SHIFT_COLORS = {
    "A": "#0d6efd",
    "B": "#198754",
    "C": "#ffc107",
    "G": "#6f42c1",
}


# --------------------------------------------------
# PROJECT MEMBERSHIP HELPER
# --------------------------------------------------
def get_member_project_ids_for_user(user_id_obj: ObjectId):
    """
    Finds project membership via:
    1. user.project_ids
    2. shifts belonging to the user
    """
    project_ids = set()

    user = mongo.db.users.find_one({"_id": user_id_obj}) or {}
    raw = user.get("project_ids", [])

    for pid in raw:
        try:
            project_ids.add(ObjectId(pid))
        except:
            pass

    # Add shifts' projects
    shift_projects = mongo.db.shifts.distinct("project_id", {"user_id": user_id_obj})
    for pid in shift_projects:
        if pid:
            try:
                project_ids.add(ObjectId(pid))
            except:
                pass

    return list(project_ids)
# --------------------------------------------------
# MEMBER DASHBOARD
# --------------------------------------------------
@member_bp.route("/dashboard", endpoint="dashboard")
@member_required
def dashboard():
    user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": user_id}) or {}

    upcoming_raw = list(
        mongo.db.shifts.find({"user_id": user_id}).sort("date", 1)
    )

    upcoming = []
    for s in upcoming_raw:
        s["_id"] = str(s["_id"])
        s["user_id"] = str(s["user_id"])
        s["project_id"] = str(s.get("project_id", "")) if s.get("project_id") else ""
        upcoming.append(s)

    upcoming_list = upcoming[:5]
    all_shifts = upcoming

    projects_map = {
        str(p["_id"]): p.get("name", "")
        for p in mongo.db.projects.find()
    }

    notifications = list(
        mongo.db.notifications.find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(5)
    )

    project_ids = get_member_project_ids_for_user(user_id)

    projects = []
    for p in mongo.db.projects.find({"_id": {"$in": project_ids}}):
        projects.append({"_id": str(p["_id"]), "name": p.get("name", "")})

    return render_template(
        "member/dashboard.html",
        upcoming=upcoming_list,
        all_shifts=all_shifts,
        projects_map=projects_map,
        notifications=notifications,
        projects=projects,
        current_user_id=str(user_id),
    )


# --------------------------------------------------
# MY SCHEDULE
# --------------------------------------------------
@member_bp.route("/my-schedule", endpoint="my_schedule")
@member_required
def my_schedule():
    current_user_id = ObjectId(session["user_id"])

    project_ids = get_member_project_ids_for_user(current_user_id)

    projects = []
    if project_ids:
        for p in mongo.db.projects.find({"_id": {"$in": project_ids}}).sort("name", 1):
            p["_id"] = str(p["_id"])
            projects.append(p)

    selected_project = request.args.get("project_id")
    selected_pid_obj = None

    if selected_project:
        try:
            selected_pid_obj = ObjectId(selected_project)
            if selected_pid_obj not in project_ids:
                selected_pid_obj = None
        except:
            selected_pid_obj = None

    if not selected_pid_obj and projects:
        selected_pid_obj = ObjectId(projects[0]["_id"])
        selected_project = projects[0]["_id"]

    # TEAM MEMBERS LIST (PROJECT-WISE)
    team_members_safe = []
    if selected_pid_obj:
        team_members = mongo.db.users.find({
            "role": "member",
            "project_ids": selected_pid_obj
        })
        for u in team_members:
            team_members_safe.append({
                "_id": str(u["_id"]),
                "name": u.get("name", ""),
                "email": u.get("email", "")
            })

    return render_template(
        "member/my_schedule.html",
        projects=projects,
        selected_project=selected_project,
        team_members=team_members_safe,
        current_user_id=str(current_user_id),
    )


# --------------------------------------------------
# API: MY SHIFTS (NO PROFILE PIC → NO FLICKER)
# --------------------------------------------------
@member_bp.route("/api/my_shifts")
@member_required
def api_my_shifts():
    user_id = ObjectId(session["user_id"])
    shifts = list(mongo.db.shifts.find({"user_id": user_id}).sort("date", 1))

    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in mongo.db.projects.find()
    }

    events = []
    for s in shifts:
        date_str = s.get("date")
        if not date_str:
            continue

        shift_code = s.get("shift_code", "")
        start_time = s.get("start_time", "09:00")
        end_time = s.get("end_time", "17:00")

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = f"{date_str}T{start_time}:00"

        if shift_code == "C":
            end_date = date_obj + timedelta(days=1)
            end = f"{end_date.isoformat()}T{end_time}:00"
        else:
            end = f"{date_str}T{end_time}:00"

        project_name = projects_map.get(str(s.get("project_id")), "General")
        task = s.get("task", "")

        tooltip = f"You • {project_name} • {shift_code}"
        if task:
            tooltip += f" • {task}"

        events.append({
            "id": str(s["_id"]),
            "title": f"{project_name}: Me – {shift_code}",
            "start": start,
            "end": end,
            "backgroundColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderColor": "#ff0000",
            "borderWidth": 3,
            "extendedProps": {
                "user_id": str(user_id),
                "project": project_name,
                "task": task,
                "shift_code": shift_code,
                "tooltip": tooltip,
                "is_my_shift": True,
            }
        })

    return jsonify(events)


# --------------------------------------------------
# API: ALL TEAM SHIFTS (NO PROFILE PIC → FIXED)
# --------------------------------------------------
@member_bp.route("/api/all_team_shifts")
@member_required
def api_all_team_shifts():
    current_user_id = ObjectId(session["user_id"])

    project_ids = get_member_project_ids_for_user(current_user_id)

    if project_ids:
        visibility_query = {
            "$or": [
                {"user_id": current_user_id},
                {"project_id": {"$in": project_ids}},
            ]
        }
    else:
        visibility_query = {"user_id": current_user_id}

    shifts = mongo.db.shifts.find(visibility_query).sort("date", 1)

    users_map = {
        str(u["_id"]): u.get("name", "Unknown")
        for u in mongo.db.users.find({"role": "member"})
    }

    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in mongo.db.projects.find()
    }

    events = []
    for s in shifts:
        date_str = s.get("date")
        if not date_str:
            continue

        uid = str(s.get("user_id"))
        uname = users_map.get(uid, "Unknown")
        shift_code = s.get("shift_code", "")
        task = s.get("task", "")

        start_time = s.get("start_time", "09:00")
        end_time = s.get("end_time", "17:00")

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = f"{date_str}T{start_time}:00"

        if shift_code == "C":
            end = f"{(date_obj + timedelta(days=1)).isoformat()}T{end_time}:00"
        else:
            end = f"{date_str}T{end_time}:00"

        project_name = projects_map.get(str(s.get("project_id")), "General")

        is_my_shift = (uid == str(current_user_id))

        tooltip = f"{uname} • {project_name} • {shift_code}"
        if task:
            tooltip += f" • {task}"

        events.append({
            "id": str(s["_id"]),
            "title": f"{project_name}: {uname} – {shift_code}",
            "start": start,
            "end": end,
            "backgroundColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderColor": "#ff0000" if is_my_shift else SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderWidth": 3 if is_my_shift else 1,
            "extendedProps": {
                "user_id": uid,
                "user": uname,
                "project": project_name,
                "task": task,
                "shift_code": shift_code,
                "tooltip": tooltip,
                "is_my_shift": is_my_shift
            }
        })

    return jsonify(events)
# --------------------------------------------------
# API: ALL MEMBERS PLANNED SHIFTS (PROJECT-WISE)
# --------------------------------------------------
@member_bp.route("/api/all_members_planned_shifts")
@member_required
def api_all_members_planned_shifts():
    current_user_id_obj = ObjectId(session["user_id"])
    current_user_id = str(current_user_id_obj)

    project_ids = get_member_project_ids_for_user(current_user_id_obj)

    if project_ids:
        visibility_query = {
            "$or": [
                {"user_id": current_user_id_obj},
                {"project_id": {"$in": project_ids}},
            ]
        }
    else:
        visibility_query = {"user_id": current_user_id_obj}

    shifts = mongo.db.shifts.find(visibility_query).sort("date", 1)

    users_map = {
        str(u["_id"]): u.get("name", "Unknown")
        for u in mongo.db.users.find({"role": "member"})
    }

    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in mongo.db.projects.find()
    }

    events = []
    for s in shifts:
        date_str = s.get("date")
        if not date_str:
            continue

        user_id = str(s.get("user_id"))
        user_name = users_map.get(user_id, "Unknown")

        shift_code = s.get("shift_code", "")
        task = s.get("task", "")

        start_time = s.get("start_time", "09:00")
        end_time = s.get("end_time", "17:00")

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = f"{date_str}T{start_time}:00"
        if shift_code == "C":
            end = f"{(date_obj + timedelta(days=1)).isoformat()}T{end_time}:00"
        else:
            end = f"{date_str}T{end_time}:00"

        project_name = projects_map.get(str(s.get("project_id")), "General")

        is_my_shift = (user_id == current_user_id)

        tooltip = f"{user_name} • {project_name} • {shift_code}"
        if task:
            tooltip += f" • {task}"

        events.append({
            "id": str(s["_id"]),
            "title": f"{project_name}: {user_name} – {shift_code}",
            "start": start,
            "end": end,
            "backgroundColor": SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderColor": "#ff0000" if is_my_shift else SHIFT_COLORS.get(shift_code, "#0dcaf0"),
            "borderWidth": 3 if is_my_shift else 1,
            "extendedProps": {
                "user_id": user_id,
                "user": user_name,
                "project": project_name,
                "task": task,
                "shift_code": shift_code,
                "tooltip": tooltip,
                "is_my_shift": is_my_shift,
            }
        })

    return jsonify(events)


# --------------------------------------------------
# ALL MEMBERS SHIFTS PAGE (TABLE VIEW + CALENDAR)
# --------------------------------------------------
@member_bp.route("/all-members-shifts")
@member_required
def all_members_shifts():
    current_user_id_obj = ObjectId(session["user_id"])
    current_user_id = str(current_user_id_obj)

    project_ids = get_member_project_ids_for_user(current_user_id_obj)

    if project_ids:
        visibility_query = {
            "$or": [
                {"user_id": current_user_id_obj},
                {"project_id": {"$in": project_ids}},
            ]
        }
    else:
        visibility_query = {"user_id": current_user_id_obj}

    raw_shifts = list(mongo.db.shifts.find(visibility_query).sort("date", 1))

    users_map = {
        str(u["_id"]): {
            "name": u.get("name", "Unknown"),
            "email": u.get("email", "")
        }
        for u in mongo.db.users.find({"role": "member"})
    }

    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in mongo.db.projects.find()
    }

    all_shifts = []
    for s in raw_shifts:
        uid = str(s.get("user_id"))
        uinfo = users_map.get(uid, {"name": "Unknown", "email": ""})

        pid = str(s.get("project_id")) if s.get("project_id") else None
        pname = projects_map.get(pid, "General") if pid else "General"

        all_shifts.append({
            "_id": str(s.get("_id")),
            "date": s.get("date"),
            "shift_code": s.get("shift_code"),
            "start_time": s.get("start_time", "09:00"),
            "end_time": s.get("end_time", "17:00"),
            "task": s.get("task", ""),
            "project_id": pid,
            "project_name": pname,
            "user_id": uid,
            "user_name": uinfo["name"],
            "user_email": uinfo["email"]
        })

    return render_template(
        "member/all_members_shifts.html",
        all_shifts=all_shifts,
        projects_map=projects_map,
        users_map=users_map,
        current_user_id=current_user_id,
        start_date=request.args.get("start_date", ""),
        end_date=request.args.get("end_date", "")
    )


# --------------------------------------------------
# EXPORT SHIFTS TO PDF
# --------------------------------------------------
@member_bp.route("/export-shifts-pdf")
@member_required
def export_shifts_pdf():
    if not REPORTLAB_AVAILABLE:
        flash("Install reportlab to enable PDF export.", "warning")
        return redirect("/member/all-members-shifts")

    current_user = ObjectId(session["user_id"])
    project_ids = get_member_project_ids_for_user(current_user)

    if project_ids:
        visibility_query = {
            "$or": [
                {"user_id": current_user},
                {"project_id": {"$in": project_ids}},
            ]
        }
    else:
        visibility_query = {"user_id": current_user}

    shifts = list(mongo.db.shifts.find(visibility_query).sort("date", 1))

    users_map = {
        str(u["_id"]): u.get("name", "Unknown")
        for u in mongo.db.users.find({"role": "member"})
    }

    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in mongo.db.projects.find()
    }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    title = Paragraph("Shift Schedule Report", styles["Heading1"])

    content = [title, Spacer(1, 12)]

    table_data = [["Date", "Member", "Shift", "Time", "Project", "Task"]]

    for s in shifts:
        uid = str(s.get("user_id"))
        uname = users_map.get(uid, "Unknown")

        pid = str(s.get("project_id"))
        pname = projects_map.get(pid, "General")

        table_data.append([
            s.get("date"),
            uname,
            s.get("shift_code", ""),
            f"{s.get('start_time', '')} - {s.get('end_time', '')}",
            pname,
            s.get("task", "") or "-"
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))

    content.append(table)
    doc.build(content)

    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=shift_schedule.pdf"}
    )


# --------------------------------------------------
# REQUEST SHIFT CHANGE
# --------------------------------------------------
@member_bp.route("/request-change", methods=["GET", "POST"])
@member_required
def request_shift_change():
    user_id = ObjectId(session["user_id"])

    if request.method == "POST":
        mongo.db.shift_change_requests.insert_one({
            "user_id": user_id,
            "date": request.form["date"],
            "requested_shift": request.form["new_shift"],
            "reason": request.form["reason"],
            "status": "pending",
            "created_at": datetime.utcnow(),
        })
        flash("Shift change request submitted.", "success")
        return redirect("/member/dashboard")

    return render_template("member/request_shift_change.html",
                           today_date=date.today().isoformat())


# --------------------------------------------------
# REQUEST SHIFT SWAP
# --------------------------------------------------
@member_bp.route("/request-swap", methods=["GET", "POST"])
@member_required
def request_swap():
    user_id = ObjectId(session["user_id"])
    users = list(mongo.db.users.find({"role": "member"}))

    if request.method == "POST":
        mongo.db.shift_swap_requests.insert_one({
            "requester_id": user_id,
            "target_user_id": ObjectId(request.form["target_user"]),
            "date": request.form["date"],
            "reason": request.form["reason"],
            "status": "pending",
            "created_at": datetime.utcnow(),
        })
        flash("Shift swap request submitted.", "success")
        return redirect("/member/dashboard")

    return render_template("member/request_swap.html",
                           users=users,
                           today_date=date.today().isoformat())


# --------------------------------------------------
# PROFILE (UPLOAD)
# --------------------------------------------------
@member_bp.route("/profile", methods=["GET", "POST"])
@member_required
def profile():
    user_id = ObjectId(session["user_id"])
    user = mongo.db.users.find_one({"_id": user_id})

    if request.method == "POST":
        file = request.files.get("profile_picture")

        if file and allowed_file(file.filename):
            filename = f"{user_id}.jpg"
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            mongo.db.users.update_one(
                {"_id": user_id}, {"$set": {"profile_picture": filename}}
            )

            flash("Profile updated.", "success")
            return redirect("/member/profile")

        flash("Invalid file format.", "danger")

    return render_template(
        "member/profile.html",
        user=user,
        profile_pic=user.get("profile_picture", "default.png")
    )


# --------------------------------------------------
# TASK HANDOVER
# --------------------------------------------------
@member_bp.route("/task-handover", methods=["GET", "POST"])
@member_required
def task_handover():
    current_user_id = ObjectId(session["user_id"])
    project_ids = get_member_project_ids_for_user(current_user_id)

    projects = [
        {"_id": str(p["_id"]), "name": p.get("name")}
        for p in mongo.db.projects.find({"_id": {"$in": project_ids}})
    ]

    selected_project = request.args.get("project_id") or ""
    selected_date = request.args.get("date") or date.today().isoformat()

    task_entries = []

    if selected_project:
        try:
            selected_pid = ObjectId(selected_project)
            task_entries = list(
                mongo.db.shift_logs.find({
                    "project_id": str(selected_pid),
                    "date": selected_date
                }).sort("created_at", -1)
            )
        except:
            pass

    if request.method == "POST":
        pid = request.form["project_id"]
        dt = request.form["date"]
        sc = request.form["shift_code"]
        comp = request.form["task_completed"]
        todo = request.form["task_to_do"]

        mongo.db.shift_logs.insert_one({
            "project_id": pid,
            "date": dt,
            "shift_code": sc,
            "user_id": current_user_id,
            "works_completed": comp,
            "works_to_do": todo,
            "created_at": datetime.utcnow(),
        })

        flash("Task logged.", "success")
        return redirect(f"/member/task-handover?project_id={pid}&date={dt}")

    return render_template(
        "member/task_handover.html",
        projects=projects,
        selected_project=selected_project,
        selected_date=selected_date,
        task_entries=task_entries
    )


# --------------------------------------------------
# VIEW SHIFT LOG
# --------------------------------------------------
@member_bp.route("/view-shift-log")
@member_required
def view_shift_log():
    current_user_id = ObjectId(session["user_id"])
    project_ids = get_member_project_ids_for_user(current_user_id)

    projects = [
        {"_id": str(p["_id"]), "name": p.get("name")}
        for p in mongo.db.projects.find({"_id": {"$in": project_ids}})
    ]

    selected_project = request.args.get("project_id") or ""
    selected_date = request.args.get("date") or date.today().isoformat()

    log_entries = []

    if selected_project:
        try:
            pid = ObjectId(selected_project)
            shifts = list(
                mongo.db.shifts.find({
                    "project_id": pid,
                    "date": selected_date
                })
            )
            shift_ids = [str(s["_id"]) for s in shifts]

            log_entries_raw = list(
                mongo.db.shift_logs.find({"shift_id": {"$in": shift_ids}})
            )

            users_map = {
                str(u["_id"]): u for u in mongo.db.users.find()
            }

            for log in log_entries_raw:
                author = users_map.get(str(log.get("user_id")), {})
                log["author"] = author
                log_entries.append(log)

        except:
            pass

    return render_template(
        "member/view_shift_log.html",
        projects=projects,
        selected_project=selected_project,
        selected_date=selected_date,
        log_entries=log_entries
    )
