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


# --------------------------------------------
# MEMBER DASHBOARD
# --------------------------------------------
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


# --------------------------------------------
# MEMBER MY SCHEDULE CALENDAR
# --------------------------------------------
@member_bp.route("/my-schedule")
@member_required
def my_schedule():
    return render_template("member/my_schedule.html")


@member_bp.route("/api/my_shifts")
@member_required
def api_my_shifts():
    user_id = ObjectId(session["user_id"])
    shifts = list(mongo.db.shifts.find({"user_id": user_id}))

    # Shift color mapping
    SHIFT_COLORS = {
        "A": "#0d6efd",  # blue
        "B": "#198754",  # green
        "C": "#ffc107",  # yellow
        "G": "#6f42c1",  # purple
    }
    
    result = []
    for s in shifts:
        start = f"{s['date']}T{s.get('start_time','09:00')}:00"
        end = f"{s['date']}T{s.get('end_time','17:00')}:00"
        shift_code = s.get('shift_code', '')
        color = SHIFT_COLORS.get(shift_code, "#0dcaf0")  # default cyan

        result.append({
            "id": str(s["_id"]),
            "title": f"{shift_code} – {s.get('task', '')}",
            "start": start,
            "end": end,
            "backgroundColor": color,
            "borderColor": color,
        })
    return jsonify(result)


# --------------------------------------------
# REQUEST SHIFT CHANGE
# --------------------------------------------
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


# --------------------------------------------
# REQUEST SHIFT SWAP
# --------------------------------------------
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
