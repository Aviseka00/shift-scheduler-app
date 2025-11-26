from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session, jsonify
)
from bson.objectid import ObjectId
from datetime import datetime
from extensions import mongo

member_bp = Blueprint("member", __name__, url_prefix="/member")


def member_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "member":
            flash("Please login as a team member.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


# -------------------------------------------------------------------
# MEMBER DASHBOARD
# -------------------------------------------------------------------
@member_bp.route("/dashboard")
@member_required
def dashboard():
    user_id = ObjectId(session["user_id"])
    upcoming = list(
        mongo.db.shifts.find({"user_id": user_id}).sort("date", 1).limit(5)
    )

    projects_map = {
        str(p["_id"]): p["name"] for p in mongo.db.projects.find()
    }

    return render_template(
        "member/dashboard.html",
        upcoming=upcoming,
        projects_map=projects_map
    )


# -------------------------------------------------------------------
# MEMBER SCHEDULE CALENDAR PAGE
# -------------------------------------------------------------------
@member_bp.route("/my-schedule")
@member_required
def my_schedule():
    """
    Renders the member schedule page which shows:
    - Own shifts + tasks
    - Other members' shifts (same projects only)
    """
    user_id = ObjectId(session["user_id"])
    user = mongo.db.users.find_one({"_id": user_id})

    # For side panel / context: list the projects + teammates in those projects
    member_project_ids = user.get("project_ids", []) if user else []
    if not isinstance(member_project_ids, list):
        member_project_ids = [member_project_ids]

    projects = list(mongo.db.projects.find(
        {"_id": {"$in": member_project_ids}})) if member_project_ids else []

    teammates = []
    if member_project_ids:
        teammates = list(mongo.db.users.find({
            "role": "member",
            "project_ids": {"$in": member_project_ids},
            "_id": {"$ne": user_id}
        }))

    return render_template(
        "member/my_schedule.html",
        projects=projects,
        teammates=teammates,
    )


# -------------------------------------------------------------------
# MEMBER CALENDAR DATA (MAIN LOGIC FOR OPTION A)
# -------------------------------------------------------------------
@member_bp.route("/api/my_shifts")
@member_required
def api_my_shifts():
    """
    Returns unified calendar data for member:
    - Own shifts + tasks
    - Other members' shifts (same project only)
    - NO tasks from others
    """
    current_user_id = ObjectId(session["user_id"])

    # 1. Fetch logged-in user
    user = mongo.db.users.find_one({"_id": current_user_id})
    if not user:
        return jsonify([])

    # project_ids is stored as a list of ObjectIds during registration
    project_ids = user.get("project_ids", []) or []
    if not isinstance(project_ids, list):
        project_ids = [project_ids]

    # 2. Fetch shifts only for projects the member belongs to
    if project_ids:
        query = {"project_id": {"$in": project_ids}}
    else:
        # Fallback: show only own shifts if member has no project mapping
        query = {"user_id": current_user_id}

    shifts = list(mongo.db.shifts.find(query))

    # Map user_id -> name for nicer titles
    users_map = {
        str(u["_id"]): u.get("name", "Unknown")
        for u in mongo.db.users.find()
    }

    # Shift color mapping
    SHIFT_COLORS = {
        "A": "#0d6efd",  # blue
        "B": "#198754",  # green
        "C": "#ffc107",  # yellow
        "G": "#6f42c1",  # purple
    }

    events = []

    for s in shifts:
        date_str = s["date"]  # "YYYY-MM-DD"
        start_time = s.get("start_time", "09:00")
        end_time = s.get("end_time", "17:00")

        start = f"{date_str}T{start_time}:00"
        end = f"{date_str}T{end_time}:00"

        shift_code = s.get("shift_code", "")
        color = SHIFT_COLORS.get(shift_code, "#0dcaf0")  # default cyan

        uid = s.get("user_id")
        uid_str = str(uid) if uid else ""
        is_self = (uid == current_user_id)

        member_name = users_map.get(uid_str, "Unknown")

        # Title rules:
        # - For self: show shift + task
        # - For others: only show name + shift (no task)
        if is_self:
            task = s.get("task", "")
            if task:
                title = f"Me – {shift_code} – {task}"
            else:
                title = f"Me – {shift_code}"
        else:
            title = f"{member_name} – {shift_code}"

        events.append({
            "id": str(s["_id"]),
            "title": title,
            "start": start,
            "end": end,
            "backgroundColor": color,
            "borderColor": color,
        })

    return jsonify(events)


# -------------------------------------------------------------------
# REQUEST SHIFT CHANGE
# -------------------------------------------------------------------
@member_bp.route("/request-change", methods=["GET", "POST"])
@member_required
def request_shift_change():
    user_id = ObjectId(session["user_id"])

    if request.method == "POST":
        date = request.form.get("date")
        new_shift = request.form.get("new_shift")
        reason = request.form.get("reason")

        mongo.db.shift_change_requests.insert_one({
            "user_id": user_id,
            "date": date,
            "requested_shift": new_shift,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.utcnow()
        })

        flash("Shift change request submitted!", "success")
        return redirect(url_for("member.dashboard"))

    return render_template("member/request_shift_change.html")


# -------------------------------------------------------------------
# REQUEST SHIFT SWAP
# -------------------------------------------------------------------
@member_bp.route("/request-swap", methods=["GET", "POST"])
@member_required
def request_swap():
    user_id = ObjectId(session["user_id"])
    users = list(mongo.db.users.find({"role": "member"}))

    if request.method == "POST":
        target_user = ObjectId(request.form.get("target_user"))
        date = request.form.get("date")
        reason = request.form.get("reason")

        mongo.db.shift_swap_requests.insert_one({
            "requester_id": user_id,
            "target_user_id": target_user,
            "date": date,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.utcnow()
        })

        flash("Shift swap request submitted!", "success")
        return redirect(url_for("member.dashboard"))

    return render_template("member/request_swap.html", users=users)
