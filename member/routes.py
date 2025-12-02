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
# PDF GENERATION SUPPORT (REPORTLAB)
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
# DASHBOARD
# --------------------------------------------------
@member_bp.route("/dashboard", endpoint="dashboard")
@member_required
def dashboard():
    """
    Member dashboard:
    - Shows top 5 upcoming shifts list
    - Passes all_shifts (JSON-safe) for any JS use
    - Shows notifications
    - Shows projects the member belongs to
    """
    user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": user_id}) or {}

    # Load raw shifts for this member
    upcoming_raw = list(
        mongo.db.shifts.find({"user_id": user_id}).sort("date", 1)
    )

    # Make ObjectIds JSON-safe (convert to string)
    upcoming = []
    for s in upcoming_raw:
        s["_id"] = str(s["_id"])
        s["user_id"] = str(s["user_id"])
        if "project_id" in s and s["project_id"]:
            try:
                s["project_id"] = str(s["project_id"])
            except Exception:
                s["project_id"] = ""
        else:
            s["project_id"] = ""
        upcoming.append(s)

    # For list view (top 5)
    upcoming_list = upcoming[:5] if len(upcoming) > 5 else upcoming

    # all_shifts used in dashboard JS (tojson)
    all_shifts = upcoming

    projects_map = {str(p["_id"]): p.get("name", "") for p in mongo.db.projects.find()}

    notifications = list(
        mongo.db.notifications.find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(5)
    )

    # Member's projects
    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except Exception:
            pass

    projects = []
    if project_ids:
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
# MY SCHEDULE (PERSONAL + TEAM VIEW)
# --------------------------------------------------
@member_bp.route("/my-schedule", endpoint="my_schedule")
@member_required
def my_schedule():
    """
    My Schedule page:
    - Uses /member/api/my_shifts for personal calendar
    - Uses /member/api/all_team_shifts for global team calendar
    """
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}

    # Extract project IDs safely
    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except Exception:
            pass

    # Load projects this member belongs to
    projects = []
    if project_ids:
        projects = list(
            mongo.db.projects.find({"_id": {"$in": project_ids}}).sort("name", 1)
        )
    for p in projects:
        p["_id"] = str(p["_id"])

    selected_project = request.args.get("project_id")
    selected_pid_obj = None

    if selected_project:
        try:
            selected_pid_obj = ObjectId(selected_project)
        except Exception:
            selected_pid_obj = None
            selected_project = None

        if selected_pid_obj not in project_ids:
            selected_pid_obj = None
            selected_project = None

    # default → first project, if any
    if not selected_project and projects:
        selected_pid_obj = ObjectId(projects[0]["_id"])
        selected_project = projects[0]["_id"]

    # Build team member list for selected project
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

    current_user_id_str = str(current_user_id)

    return render_template(
        "member/my_schedule.html",
        projects=projects,
        selected_project=selected_project,
        team_members=team_members_safe,
        current_user_id=current_user_id_str,
    )


# --------------------------------------------------
# API: MY SHIFTS (PERSONAL CALENDAR)
# --------------------------------------------------
@member_bp.route("/api/my_shifts", endpoint="api_my_shifts")
@member_required
def api_my_shifts():
    """
    Returns ONLY the current user's shifts for their personal calendar.
    Shows all shifts assigned to the user, regardless of project.
    """
    user_id = ObjectId(session["user_id"])
    user = mongo.db.users.find_one({"_id": user_id}) or {}
    profile_pic = user.get("profile_picture", "default.png")

    # All shifts for this user
    shifts = list(mongo.db.shifts.find({"user_id": user_id}).sort("date", 1))
    print(f"DEBUG api_my_shifts: Found {len(shifts)} shifts for user {user_id}")

    projects_map = {str(p["_id"]): p.get("name", "General") for p in mongo.db.projects.find()}

    events = []
    for s in shifts:
        date_str = s.get("date")
        if not date_str:
            continue

        shift_code = s.get("shift_code", "")
        start_time = s.get("start_time") or "09:00"
        end_time = s.get("end_time") or "17:00"

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            continue

        start = f"{date_str}T{start_time}:00"

        # Night shift continues into next day
        if shift_code == "C":
            end_date = date_obj + timedelta(days=1)
            end = f"{end_date.isoformat()}T{end_time}:00"
        else:
            end = f"{date_str}T{end_time}:00"

        project_name = "General"
        pid = s.get("project_id")
        if pid:
            project_name = projects_map.get(str(pid), "General")

        task = s.get("task", "")

        title_parts = [shift_code] if shift_code else []
        if task:
            title_parts.append(task)
        if project_name and project_name != "General":
            title_parts.append(f"[{project_name}]")
        title = " - ".join(title_parts) if title_parts else "My Shift"

        tooltip = f"My {shift_code} Shift\n"
        tooltip += f"Project: {project_name}\n"
        tooltip += f"Time: {start_time} - {end_time}\n"
        if task:
            tooltip += f"Task: {task}"

        base_color = SHIFT_COLORS.get(shift_code, "#0dcaf0")

        events.append({
            "id": str(s["_id"]),
            "title": title,
            "start": start,
            "end": end,
            "backgroundColor": base_color,
            "borderColor": "#ff0000",
            "borderWidth": 3,
            "extendedProps": {
                "profile_pic": profile_pic,
                "user_id": str(user_id),
                "shift_code": shift_code,
                "project": project_name,
                "task": task,
                "start_time": start_time,
                "end_time": end_time,
                "tooltip": tooltip,
                "is_my_shift": True
            }
        })

    print(f"DEBUG api_my_shifts: Returning {len(events)} events")
    if events:
        print(f"DEBUG api_my_shifts: First event: {events[0]}")
    return jsonify(events)


# --------------------------------------------------
# API: ALL TEAM SHIFTS (ALL MEMBERS, ALL PROJECTS)
#  -> USED BY DASHBOARD + MY_SCHEDULE + ALL_MEMBERS_SHIFTS
# --------------------------------------------------
@member_bp.route("/api/all_team_shifts", endpoint="api_all_team_shifts")
@member_required
def api_all_team_shifts():
    """
    Returns ALL shifts from ALL members (across all projects).
    Members can see their own and everyone else's shifts in calendar.
    """
    try:
        current_user_id = ObjectId(session["user_id"])

        # Get all shifts (across projects)
        shifts = list(mongo.db.shifts.find({}).sort("date", 1))

        # All members
        users_list = list(mongo.db.users.find({"role": "member"}))
        users_map = {
            str(u["_id"]): {
                "name": u.get("name", "Unknown"),
                "email": u.get("email", ""),
                "profile_pic": u.get("profile_picture", "default.png")
            }
            for u in users_list
        }

        # All projects
        projects_map = {str(p["_id"]): p.get("name", "General") for p in mongo.db.projects.find()}

        events = []
        for s in shifts:
            try:
                date_str = s.get("date")
                if not date_str:
                    continue

                shift_code = s.get("shift_code", "")
                start_time = s.get("start_time") or "09:00"
                end_time = s.get("end_time") or "17:00"
                s_user_id = str(s.get("user_id", ""))

                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    continue

                start = f"{date_str}T{start_time}:00"
                if shift_code == "C":
                    end_date = date_obj + timedelta(days=1)
                    end = f"{end_date.isoformat()}T{end_time}:00"
                else:
                    end = f"{date_str}T{end_time}:00"

                user_info = users_map.get(
                    s_user_id,
                    {"name": "Unknown", "email": "", "profile_pic": "default.png"}
                )
                user_name = user_info["name"]
                project_name = "General"
                if s.get("project_id"):
                    project_name = projects_map.get(str(s["project_id"]), "General")

                task = s.get("task", "")

                is_my_shift = (s_user_id == str(current_user_id))

                if is_my_shift:
                    title = f"{project_name}: Me – {shift_code}"
                else:
                    title = f"{project_name}: {user_name} – {shift_code}"

                base_color = SHIFT_COLORS.get(shift_code, "#0dcaf0")

                if is_my_shift:
                    bg_color = base_color
                    border_color = "#ff0000"
                    border_width = 3
                else:
                    bg_color = base_color
                    border_color = base_color
                    border_width = 1

                tooltip = f"{user_name} • {project_name} • {shift_code} • {task}"

                events.append({
                    "id": str(s["_id"]),
                    "title": title,
                    "start": start,
                    "end": end,
                    "backgroundColor": bg_color,
                    "borderColor": border_color,
                    "borderWidth": border_width,
                    "extendedProps": {
                        "user_id": s_user_id,
                        "user_name": user_name,
                        "user_email": user_info["email"],
                        "is_my_shift": is_my_shift,
                        "project": project_name,
                        "task": task,
                        "shift_code": shift_code,
                        "tooltip": tooltip,
                        "profile_pic": user_info["profile_pic"],
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                })
            except Exception as e:
                current_app.logger.error(f"Error processing shift {s.get('_id')}: {str(e)}")
                continue

        return jsonify(events)
    except Exception as e:
        current_app.logger.error(f"Error in api_all_team_shifts: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# --------------------------------------------------
# API: ALL MEMBERS PLANNED SHIFTS (GENERIC)
#  -> USED BY all_members_shifts.html calendar
# --------------------------------------------------
@member_bp.route("/api/all_members_planned_shifts", endpoint="api_all_members_planned_shifts")
@member_required
def api_all_members_planned_shifts():
    """
    Returns all shifts in a generic format.
    Used by all_members_shifts.html for FullCalendar.
    """
    current_user_id = str(ObjectId(session["user_id"]))

    shifts = list(mongo.db.shifts.find().sort("date", 1))

    users_list = list(mongo.db.users.find({"role": "member"}))
    users_map = {
        str(u["_id"]): {
            "name": u.get("name", "Unknown"),
            "profile_pic": u.get("profile_picture", "default.png")
        }
        for u in users_list
    }

    projects_list = list(mongo.db.projects.find())
    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in projects_list
    }

    events = []
    for s in shifts:
        date_str = s.get("date")
        if not date_str:
            continue

        shift_code = s.get("shift_code", "")
        start_time = s.get("start_time", "09:00")
        end_time = s.get("end_time", "17:00")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start = f"{date_str}T{start_time}:00"
            if shift_code == "C":
                end_date = date_obj + timedelta(days=1)
                end = f"{end_date.isoformat()}T{end_time}:00"
            else:
                end = f"{date_str}T{end_time}:00"
        except Exception:
            continue

        user_id = str(s.get("user_id"))
        user_info = users_map.get(user_id, {"name": "Unknown", "profile_pic": "default.png"})
        user_name = user_info["name"]
        profile_pic = user_info["profile_pic"]

        project_id = str(s.get("project_id")) if s.get("project_id") else None
        project_name = projects_map.get(project_id, "General") if project_id else "General"
        task = s.get("task", "")

        is_my_shift = (user_id == current_user_id)
        color = SHIFT_COLORS.get(shift_code, "#0dcaf0")
        tooltip = f"{user_name} • {project_name} • {shift_code} • {task}"

        events.append({
            "id": str(s.get("_id")),
            "title": f"{project_name}: {user_name} – {shift_code}",
            "start": start,
            "end": end,
            "backgroundColor": color,
            "borderColor": "#ff0000" if is_my_shift else color,
            "borderWidth": 3 if is_my_shift else 1,
            "extendedProps": {
                "shift_id": str(s.get("_id")),
                "user": user_name,
                "user_id": user_id,
                "profile_pic": profile_pic,
                "project": project_name,
                "task": task,
                "shift_code": shift_code,
                "tooltip": tooltip,
                "is_my_shift": is_my_shift,
            },
        })

    print(
        "DEBUG api_all_members_planned_shifts: Found "
        + str(len(shifts))
        + " shifts, returning "
        + str(len(events))
        + " events"
    )
    return jsonify(events)


# --------------------------------------------------
# VIEW ALL MEMBERS’ SHIFTS (ACROSS ALL PROJECTS)
#  -> /member/all-members-shifts
# --------------------------------------------------
@member_bp.route("/all-members-shifts", endpoint="all_members_shifts")
@member_required
def all_members_shifts():
    """
    View page that shows all members' planned shifts in a table
    + a calendar (via /member/api/all_members_planned_shifts).
    """
    current_user_id = str(ObjectId(session["user_id"]))

    # Get all shifts from database
    all_shifts_raw = list(mongo.db.shifts.find().sort("date", 1))

    # Get all users
    all_users = list(mongo.db.users.find({"role": "member"}))
    users_map = {
        str(u["_id"]): {
            "name": u.get("name", "Unknown"),
            "email": u.get("email", ""),
            "profile_pic": u.get("profile_picture", "default.png")
        }
        for u in all_users
    }

    # Get all projects
    all_projects = list(mongo.db.projects.find())
    projects_map = {str(p["_id"]): p.get("name", "General") for p in all_projects}

    # Format shifts for template table
    all_shifts = []
    for shift in all_shifts_raw:
        user_id = str(shift.get("user_id"))
        user_info = users_map.get(user_id, {
            "name": "Unknown",
            "email": "",
            "profile_pic": "default.png"
        })

        project_id = str(shift.get("project_id")) if shift.get("project_id") else None
        project_name = projects_map.get(project_id, "General") if project_id else "General"

        all_shifts.append({
            "_id": str(shift.get("_id")),
            "date": shift.get("date"),
            "shift_code": shift.get("shift_code", ""),
            "start_time": shift.get("start_time", "09:00"),
            "end_time": shift.get("end_time", "17:00"),
            "task": shift.get("task", ""),
            "project_id": project_id,
            "user_id": user_id,
            "user_name": user_info["name"],
            "user_email": user_info["email"],
            "profile_pic": user_info["profile_pic"],
        })

    # Date filter values for the form (purely for UI, JS does calendar filtering)
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    return render_template(
        "member/all_members_shifts.html",
        all_shifts=all_shifts,
        projects_map=projects_map,
        users_map=users_map,
        current_user_id=current_user_id,
        start_date=start_date,
        end_date=end_date,
    )


# --------------------------------------------------
# EXPORT SHIFTS TO PDF
# --------------------------------------------------
@member_bp.route("/export-shifts-pdf", endpoint="export_shifts_pdf")
@member_required
def export_shifts_pdf():
    """
    Export all members' shifts to PDF for printing/viewing.
    """
    if not REPORTLAB_AVAILABLE:
        flash("PDF export is not available. Please install reportlab: pip install reportlab", "warning")
        return redirect("/member/all-members-shifts")

    current_user_id = str(ObjectId(session["user_id"]))

    shifts = list(mongo.db.shifts.find().sort("date", 1))

    users_list = list(mongo.db.users.find({"role": "member"}))
    users_map = {
        str(u["_id"]): {
            "name": u.get("name", "Unknown"),
            "email": u.get("email", "")
        }
        for u in users_list
    }

    projects_list = list(mongo.db.projects.find())
    projects_map = {
        str(p["_id"]): p.get("name", "General")
        for p in projects_list
    }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#667eea"),
        spaceAfter=30,
        alignment=1,
    )
    title = Paragraph("All Members Shift Schedule", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    shifts_by_date = {}
    for s in shifts:
        date_str = s.get("date")
        if not date_str:
            continue

        if date_str not in shifts_by_date:
            shifts_by_date[date_str] = []

        user_id = str(s.get("user_id"))
        user_info = users_map.get(user_id, {"name": "Unknown", "email": ""})
        project_id = str(s.get("project_id")) if s.get("project_id") else None
        project_name = projects_map.get(project_id, "General") if project_id else "General"

        shifts_by_date[date_str].append({
            "member": user_info["name"],
            "shift": s.get("shift_code", ""),
            "time": f"{s.get('start_time', '09:00')} - {s.get('end_time', '17:00')}",
            "project": project_name,
            "task": s.get("task", ""),
            "is_my_shift": (user_id == current_user_id)
        })

    for date_str in sorted(shifts_by_date.keys()):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%A, %B %d, %Y")
        date_style = ParagraphStyle(
            "DateHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#2d3748"),
            spaceAfter=10,
            spaceBefore=20,
        )
        date_para = Paragraph(date_display, date_style)
        elements.append(date_para)

        table_data = [["Member", "Shift", "Time", "Project", "Task"]]
        for shift_info in shifts_by_date[date_str]:
            member_name = shift_info["member"]
            if shift_info["is_my_shift"]:
                member_name = f"<b>{member_name} (You)</b>"

            table_data.append([
                Paragraph(member_name, styles["Normal"]),
                shift_info["shift"],
                shift_info["time"],
                shift_info["project"],
                shift_info["task"] or "-",
            ])

        table = Table(
            table_data,
            colWidths=[2 * inch, 0.8 * inch, 1.2 * inch, 1.5 * inch, 2 * inch],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#667eea")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))

    doc.build(elements)
    buffer.seek(0)

    filename = "all_members_shifts_" + datetime.now().strftime("%Y%m%d") + ".pdf"

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=" + filename},
    )


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
            "created_at": datetime.utcnow(),
        })

        flash("Shift change request submitted!", "success")
        return redirect(url_for("member.dashboard"))

    today_date = date.today().isoformat()
    return render_template("member/request_shift_change.html", today_date=today_date)


# --------------------------------------------------
# REQUEST SHIFT SWAP
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
            "created_at": datetime.utcnow(),
        })

        flash("Shift swap request submitted!", "success")
        return redirect(url_for("member.dashboard"))

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
# TASK HANDOVER (PROJECT-WIDE COMMENT SECTION PER DATE)
# --------------------------------------------------
@member_bp.route("/task-handover", methods=["GET", "POST"], endpoint="task_handover")
@member_required
def task_handover():
    """
    Task Handover:
    - Member selects project + date + shift
    - Writes "tasks completed" & "tasks for next shift"
    - Entry is stored in shift_logs, linked to shift_id (if found)
    - All project members for that date can see these entries.
    """
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}

    # Get user's projects
    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except Exception:
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
        except Exception:
            pass

    # Default: first project if none selected
    if not selected_project and projects:
        selected_project = projects[0]["_id"]

    if request.method == "POST":
        project_id = request.form.get("project_id", "").strip()
        date_str = request.form.get("date", "").strip()
        shift_code = request.form.get("shift_code", "").strip()
        task_completed = request.form.get("task_completed", "").strip()
        task_to_do = request.form.get("task_to_do", "").strip()

        if not project_id:
            flash("Please select a project.", "warning")
            return redirect("/member/task-handover")

        if not date_str:
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

            # Try to find the corresponding shift to link with this log
            shift_doc = mongo.db.shifts.find_one({
                "user_id": current_user_id,
                "project_id": project_obj_id,
                "date": date_str,
                "shift_code": shift_code
            })
            shift_id = str(shift_doc["_id"]) if shift_doc else None

            task_entry = {
                "project_id": str(project_obj_id),
                "date": date_str,
                "shift_code": shift_code,
                "user_id": current_user_id,
                "works_completed": task_completed,
                "works_to_do": task_to_do,
                "created_at": datetime.utcnow(),
            }
            if shift_id:
                task_entry["shift_id"] = shift_id

            mongo.db.shift_logs.insert_one(task_entry)
            flash("Task handover posted successfully! All team members can see it.", "success")
            return redirect(f"/member/task-handover?project_id={project_id}&date={date_str}")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect("/member/task-handover")

    return render_template(
        "member/task_handover.html",
        projects=projects,
        selected_project=selected_project,
        selected_date=selected_date,
        task_entries=task_entries,
    )


# --------------------------------------------------
# VIEW SHIFT LOG (READ-ONLY FOR ALL MEMBERS)
# --------------------------------------------------
@member_bp.route("/view-shift-log", endpoint="view_shift_log")
@member_required
def view_shift_log():
    """
    View shift logs associated with specific project/date.
    Uses shift_id link so logs show which shift & user they belong to.
    """
    current_user_id = ObjectId(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": current_user_id}) or {}

    raw_pids = current_user.get("project_ids", [])
    project_ids = []
    for pid in raw_pids:
        try:
            project_ids.append(ObjectId(pid))
        except Exception:
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
        except Exception:
            selected_pid_obj = None
            selected_project = ""

    if not selected_project and projects:
        selected_pid_obj = ObjectId(projects[0]["_id"])
        selected_project = projects[0]["_id"]

    if selected_project is None:
        selected_project = ""

    log_entries = []
    if selected_pid_obj and selected_date:
        # First, find shifts on that project & date
        shifts = list(mongo.db.shifts.find({
            "project_id": selected_pid_obj,
            "date": selected_date
        }).sort("shift_code", 1))

        shift_ids = [str(s["_id"]) for s in shifts]

        # Find logs that reference these shifts
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
        log_entries=log_entries,
    )
