from datetime import datetime, timedelta
import csv
import io

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    Response,
)
from bson.objectid import ObjectId

from . import manager_bp
from extensions import mongo


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


def manager_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "manager":
            flash("Manager access required.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


def check_shift_conflict(user_id, date_str, exclude_shift_id=None):
    """
    Check if a user already has a shift on the given date.
    Returns (has_conflict, existing_shift) tuple.
    """
    query = {
        "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
        "date": date_str
    }
    
    existing_shift = mongo.db.shifts.find_one(query)
    
    if existing_shift:
        # If we're updating an existing shift, exclude it from conflict check
        if exclude_shift_id and str(existing_shift["_id"]) == str(exclude_shift_id):
            return False, None
        return True, existing_shift
    
    return False, None


# Color map for calendar events by shift code (fallback)
SHIFT_COLORS = {
    "A": "#0d6efd",  # blue
    "B": "#198754",  # green
    "C": "#ffc107",  # yellow
    "G": "#6f42c1",  # purple
}


@manager_bp.route("/dashboard", methods=["GET"])
@manager_required
def dashboard():
    users_count = mongo.db.users.count_documents({})
    shifts_count = mongo.db.shifts.count_documents({})
    project_count = mongo.db.projects.count_documents({})
    pending_change = mongo.db.shift_change_requests.count_documents({"status": "pending"})
    pending_swap = mongo.db.shift_swap_requests.count_documents({"status": "pending"})

    projects = list(mongo.db.projects.find().sort("created_at", -1))
    for p in projects:
        p["shift_count"] = mongo.db.shifts.count_documents({"project_id": p["_id"]})
        p["task_count"] = mongo.db.project_tasks.count_documents({"project_id": p["_id"]})

    return render_template(
        "manager/dashboard.html",
        users_count=users_count,
        shifts_count=shifts_count,
        project_count=project_count,
        pending_change=pending_change,
        pending_swap=pending_swap,
        projects=projects,
    )


@manager_bp.route("/auto-roster", methods=["POST"])
@manager_required
def auto_roster():
    start_date_str = request.form.get("start_date")
    end_date_str = request.form.get("end_date")
    project_id = request.form.get("project_id") or None

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        flash("Invalid date range", "danger")
        return redirect(url_for("manager.dashboard"))

    if end_date < start_date:
        flash("End date must be after start date", "danger")
        return redirect(url_for("manager.dashboard"))

    members = list(mongo.db.users.find({"role": "member"}))
    if not members:
        flash("No team members found to assign shifts.", "warning")
        return redirect(url_for("manager.dashboard"))

    member_ids = [m["_id"] for m in members]
    idx = 0

    day = start_date
    while day <= end_date:
        # Example: two shifts per day (A, B)
        shift_templates = {
            "A": ("08:00", "16:00"),
            "B": ("16:00", "23:00"),
        }
        for shift_code, (start_t, end_t) in shift_templates.items():
            user_id = member_ids[idx % len(member_ids)]
            idx += 1

            date_str = day.isoformat()
            
            # Check for existing shift on this date for this user
            existing_shift = mongo.db.shifts.find_one({
                "date": date_str,
                "user_id": user_id
            })
            
            if existing_shift:
                # Update existing shift instead of creating duplicate
                doc = {
                    "date": date_str,
                    "user_id": user_id,
                    "shift_code": shift_code,
                    "start_time": start_t,
                    "end_time": end_t,
                    "task": f"{shift_code} shift",
                    "updated_at": datetime.utcnow(),
                }
                if project_id:
                    doc["project_id"] = ObjectId(project_id)
                else:
                    doc["project_id"] = None

                mongo.db.shifts.update_one(
                    {"_id": existing_shift["_id"]},
                    {"$set": doc}
                )
            else:
                # Create new shift
                doc = {
                    "date": date_str,
                    "user_id": user_id,
                    "shift_code": shift_code,
                    "start_time": start_t,
                    "end_time": end_t,
                    "task": f"{shift_code} shift",
                    "updated_at": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                }
                if project_id:
                    doc["project_id"] = ObjectId(project_id)
                else:
                    doc["project_id"] = None

                mongo.db.shifts.insert_one(doc)

        day += timedelta(days=1)

    flash("Auto roster generated successfully.", "success")
    return redirect(url_for("manager.dashboard"))


@manager_bp.route("/api/shifts")
@manager_required
def api_shifts():
    """
    Returns shifts as FullCalendar events (for manager calendar).
    Optional filters: ?user_id=...&project_id=...
    """
    query = {}
    user_id = request.args.get("user_id")
    project_id = request.args.get("project_id")

    if user_id:
        query["user_id"] = ObjectId(user_id)
    if project_id:
        query["project_id"] = ObjectId(project_id)

    shifts_cursor = mongo.db.shifts.find(query)

    users_map = {str(u["_id"]): u["name"] for u in mongo.db.users.find()}
    projects_map = {str(p["_id"]): p["name"] for p in mongo.db.projects.find()}

    events = []
    for s in shifts_cursor:
        date_str = s["date"]  # "YYYY-MM-DD"
        start_time = s.get("start_time") or "09:00"
        end_time = s.get("end_time") or "17:00"
        start = f"{date_str}T{start_time}:00"
        end = f"{date_str}T{end_time}:00"

        uid = str(s["user_id"])
        pid = str(s.get("project_id")) if s.get("project_id") else None

        user_name = users_map.get(uid, "Unknown")
        project_name = projects_map.get(pid, "General") if pid else "General"
        shift_code = s.get("shift_code", "")
        task = s.get("task", "")

        # Color by shift code (A, B, C, G)
        color = SHIFT_COLORS.get(shift_code, "#0dcaf0")

        tooltip = f"{user_name} • {project_name} • {shift_code} • {task}"

        events.append(
            {
                "id": str(s["_id"]),
                "title": f"{project_name}: {user_name} – {shift_code}",
                "start": start,
                "end": end,
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "shift_id": str(s["_id"]),
                    "user": user_name,
                    "project": project_name,
                    "task": task,
                    "shift_code": shift_code,
                    "tooltip": tooltip,
                },
            }
        )

    return jsonify(events)


@manager_bp.route("/api/update-shift", methods=["POST"])
@manager_required
def api_update_shift():
    """
    Update shift date/time when dragged or resized on the calendar.
    """
    data = request.get_json(force=True)
    shift_id = data.get("id")
    start_iso = data.get("start")
    end_iso = data.get("end")

    if not shift_id or not start_iso or not end_iso:
        return jsonify({"success": False, "error": "Missing data"}), 400

    try:
        start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid datetime"}), 400

    date_str = start_dt.date().isoformat()
    start_time = start_dt.strftime("%H:%M")
    end_time = end_dt.strftime("%H:%M")

    # Get current shift to check user
    current_shift = mongo.db.shifts.find_one({"_id": ObjectId(shift_id)})
    if not current_shift:
        return jsonify({"success": False, "error": "Shift not found"}), 404

    # Check for conflict if date changed
    if current_shift.get("date") != date_str:
        has_conflict, conflicting_shift = check_shift_conflict(
            current_shift["user_id"], 
            date_str, 
            exclude_shift_id=shift_id
        )
        if has_conflict:
            return jsonify({
                "success": False, 
                "error": f"User already has a shift on {date_str}. Cannot move shift to this date."
            }), 400

    mongo.db.shifts.update_one(
        {"_id": ObjectId(shift_id)},
        {
            "$set": {
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return jsonify({"success": True})


@manager_bp.route("/team-view")
@manager_required
def team_view():
    users = list(mongo.db.users.find({"role": "member"}))
    # Convert ObjectId to string for JSON serialization
    for u in users:
        u["_id"] = str(u["_id"])
    return render_template("manager/team_view.html", users=users)


@manager_bp.route("/export/csv")
@manager_required
def export_csv():
    """
    Export all shifts as CSV (Excel compatible).
    Optional filter: ?project_id=...
    """
    project_id = request.args.get("project_id")
    query = {}
    if project_id:
        query["project_id"] = ObjectId(project_id)

    shifts = mongo.db.shifts.find(query).sort("date", 1)
    users_map = {str(u["_id"]): u["name"] for u in mongo.db.users.find()}
    projects_map = {str(p["_id"]): p["name"] for p in mongo.db.projects.find()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "User", "Project", "Shift", "Start", "End", "Task"])

    for s in shifts:
        uid = str(s["user_id"])
        pid = str(s.get("project_id")) if s.get("project_id") else None
        writer.writerow(
            [
                s["date"],
                users_map.get(uid, "Unknown"),
                projects_map.get(pid, "General") if pid else "General",
                s.get("shift_code", ""),
                s.get("start_time", ""),
                s.get("end_time", ""),
                s.get("task", ""),
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=shift_schedule.csv"},
    )


@manager_bp.route("/export/print")
@manager_required
def export_print():
    project_id = request.args.get("project_id")
    query = {}
    if project_id:
        query["project_id"] = ObjectId(project_id)

    shifts = list(mongo.db.shifts.find(query).sort("date", 1))
    users_map = {str(u["_id"]): u["name"] for u in mongo.db.users.find()}
    projects_map = {str(p["_id"]): p["name"] for p in mongo.db.projects.find()}

    return render_template(
        "manager/export_print.html",
        shifts=shifts,
        users_map=users_map,
        projects_map=projects_map,
    )


@manager_bp.route("/manage-shifts", methods=["GET", "POST"])
@manager_required
def manage_shifts():
    projects = list(mongo.db.projects.find())
    selected_date = request.args.get("date")
    selected_project = request.args.get("project_id")
    show_all_members = request.args.get("show_all", "false") == "true"
    
    # Get members - filter by project if selected and not showing all
    if selected_project and not show_all_members:
        # Get members registered under this project
        users = list(mongo.db.users.find({
            "role": "member",
            "project_ids": ObjectId(selected_project)
        }))
    else:
        # Get all members
        users = list(mongo.db.users.find({"role": "member"}))

    if request.method == "POST":
        action = request.form.get("action")
        
        # Handle task creation
        if action == "add_task":
            task_name = request.form.get("task_name")
            assigned_to = request.form.get("assigned_to")
            due_date = request.form.get("due_date")
            project_id = request.form.get("project_id")
            
            if not project_id:
                flash("Please select a project.", "danger")
                return redirect(url_for("manager.manage_shifts"))
            
            mongo.db.project_tasks.insert_one({
                "project_id": ObjectId(project_id),
                "task_name": task_name,
                "assigned_to": ObjectId(assigned_to),
                "due_date": due_date,
                "created_at": datetime.utcnow()
            })
            
            # Notify user of new task
            mongo.db.notifications.insert_one({
                "user_id": ObjectId(assigned_to),
                "message": f"New task '{task_name}' assigned to you for project.",
                "project_id": ObjectId(project_id),
                "created_at": datetime.utcnow(),
                "read": False,
            })
            
            flash("Task added successfully!", "success")
            redirect_url = url_for("manager.manage_shifts")
            if selected_project:
                redirect_url += f"?project_id={selected_project}"
            return redirect(redirect_url)
        
        # Handle shift creation/update (for both "add_shift" action and legacy form)
        if action == "add_shift" or action is None:
            date_str = request.form.get("date")
            user_id = request.form.get("user_id")
            shift_code = request.form.get("shift_code")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")
            task = request.form.get("task")
            project_id = request.form.get("project_id") or None

            if not date_str or not user_id or not shift_code:
                flash("Please fill in all required fields for shift.", "danger")
                redirect_url = url_for("manager.manage_shifts")
                if selected_project:
                    redirect_url += f"?project_id={selected_project}"
                return redirect(redirect_url)

            # Check for existing shift conflict
            existing_shift = mongo.db.shifts.find_one({
                "date": date_str,
                "user_id": ObjectId(user_id)
            })
            
            if existing_shift:
                # Update existing shift
                update_doc = {
                    "date": date_str,
                    "user_id": ObjectId(user_id),
                    "shift_code": shift_code,
                    "start_time": start_time,
                    "end_time": end_time,
                    "task": task,
                    "updated_at": datetime.utcnow(),
                }
                if project_id:
                    update_doc["project_id"] = ObjectId(project_id)
                else:
                    update_doc["project_id"] = None

                mongo.db.shifts.update_one(
                    {"_id": existing_shift["_id"]},
                    {"$set": update_doc}
                )
                
                # Notify user of shift update
                mongo.db.notifications.insert_one({
                    "user_id": ObjectId(user_id),
                    "message": f"Your shift on {date_str} has been updated.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                })
                
                flash("Shift updated successfully.", "success")
            else:
                # Create new shift
                update_doc = {
                    "date": date_str,
                    "user_id": ObjectId(user_id),
                    "shift_code": shift_code,
                    "start_time": start_time,
                    "end_time": end_time,
                    "task": task,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
                if project_id:
                    update_doc["project_id"] = ObjectId(project_id)
                else:
                    update_doc["project_id"] = None

                mongo.db.shifts.insert_one(update_doc)
                
                # Notify user of new shift
                mongo.db.notifications.insert_one({
                    "user_id": ObjectId(user_id),
                    "message": f"You have been assigned a shift on {date_str}.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                })
                
                flash("Shift created successfully.", "success")
            
            redirect_url = url_for("manager.manage_shifts", date=date_str)
            if selected_project:
                redirect_url += f"&project_id={selected_project}"
            return redirect(redirect_url)

    # Build query for shifts
    query = {}
    if selected_date:
        query["date"] = selected_date
    if selected_project:
        query["project_id"] = ObjectId(selected_project)
    
    # Get all shifts matching the query
    shifts = list(mongo.db.shifts.find(query).sort("date", 1))
    
    # Get tasks for selected project if filtering by project
    tasks = []
    if selected_project:
        tasks = list(mongo.db.project_tasks.find({"project_id": ObjectId(selected_project)}).sort("created_at", -1))
    
    # Get all members for the "show all" option
    all_members = list(mongo.db.users.find({"role": "member"}))
    
    # Convert ObjectId to string for JSON serialization
    def convert_user_for_json(user):
        user_dict = {
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user.get("email", ""),
            "role": user.get("role", "member"),
            "project_ids": [str(pid) for pid in user.get("project_ids", [])] if user.get("project_ids") else []
        }
        return user_dict
    
    users_json = [convert_user_for_json(u) for u in users]
    all_members_json = [convert_user_for_json(u) for u in all_members]
    
    # Create maps for easy lookup
    users_map = {str(u["_id"]): u["name"] for u in all_members}  # Use all_members for complete map
    projects_map = {str(p["_id"]): p["name"] for p in projects}
    
    shifts_map = {}
    if selected_date:
        # For backward compatibility
        cursor = mongo.db.shifts.find({"date": selected_date})
        for s in cursor:
            shifts_map[str(s["user_id"])] = s

    return render_template(
        "manager/manage_shifts.html",
        users=users,  # Filtered members (by project or all)
        users_json=users_json,  # JSON-serializable version
        all_members=all_members,  # All members for "show all" option
        all_members_json=all_members_json,  # JSON-serializable version
        projects=projects,
        selected_date=selected_date,
        selected_project=selected_project,
        show_all_members=show_all_members,
        shifts_map=shifts_map,
        shifts=shifts,
        tasks=tasks,
        users_map=users_map,
        projects_map=projects_map,
    )


@manager_bp.route("/edit-shift/<shift_id>", methods=["GET", "POST"])
@manager_required
def edit_shift(shift_id):
    shift = mongo.db.shifts.find_one({"_id": ObjectId(shift_id)})
    if not shift:
        flash("Shift not found.", "danger")
        return redirect(url_for("manager.dashboard"))

    projects = list(mongo.db.projects.find())
    
    # Get shift's project to filter members
    shift_project_id = shift.get("project_id")
    show_all = request.args.get("show_all", "false") == "true"
    
    # Get members - filter by project if shift has a project and not showing all
    if shift_project_id and not show_all:
        users = list(mongo.db.users.find({
            "role": "member",
            "project_ids": shift_project_id
        }))
        # Also include the current shift's user even if not in project
        current_user_id = shift.get("user_id")
        if current_user_id:
            current_user = mongo.db.users.find_one({"_id": current_user_id})
            if current_user and current_user not in users:
                users.append(current_user)
    else:
        # Get all members
        users = list(mongo.db.users.find({"role": "member"}))

    if request.method == "POST":
        date_str = request.form.get("date")
        user_id = request.form.get("user_id")
        shift_code = request.form.get("shift_code")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        task = request.form.get("task")
        project_id = request.form.get("project_id") or None

        # Check for shift conflict (excluding current shift)
        has_conflict, conflicting_shift = check_shift_conflict(user_id, date_str, exclude_shift_id=shift_id)
        
        if has_conflict:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            user_name = user["name"] if user else "Unknown"
            flash(f"Conflict: {user_name} already has a shift on {date_str}. Please choose a different date or user.", "danger")
            return redirect(url_for("manager.edit_shift", shift_id=shift_id))

        update_doc = {
            "date": date_str,
            "user_id": ObjectId(user_id),
            "shift_code": shift_code,
            "start_time": start_time,
            "end_time": end_time,
            "task": task,
            "updated_at": datetime.utcnow(),
        }
        if project_id:
            update_doc["project_id"] = ObjectId(project_id)
        else:
            update_doc["project_id"] = None

        mongo.db.shifts.update_one({"_id": ObjectId(shift_id)}, {"$set": update_doc})

        mongo.db.notifications.insert_one(
            {
                "user_id": ObjectId(user_id),
                "message": f"Your shift on {date_str} has been updated by the manager.",
                "project_id": ObjectId(project_id) if project_id else None,
                "created_at": datetime.utcnow(),
                "read": False,
            }
        )

        flash("Shift updated and user notified.", "success")
        return redirect(url_for("manager.dashboard"))

    # Get all members for the show all option
    all_users = list(mongo.db.users.find({"role": "member"}))
    
    # Convert ObjectId to string for JSON serialization
    def convert_user_for_json(user):
        user_dict = {
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user.get("email", ""),
            "role": user.get("role", "member"),
            "project_ids": [str(pid) for pid in user.get("project_ids", [])] if user.get("project_ids") else []
        }
        return user_dict
    
    users_json = [convert_user_for_json(u) for u in users]
    all_users_json = [convert_user_for_json(u) for u in all_users]
    
    return render_template(
        "manager/edit_shift.html",
        shift=shift,
        users=users,
        users_json=users_json,  # JSON-serializable version
        all_users=all_users,
        all_users_json=all_users_json,  # JSON-serializable version
        projects=projects,
        shift_project_id=shift_project_id,
        show_all=show_all,
    )


# -----------------------------------------
# DELETE SHIFT
# -----------------------------------------
@manager_bp.route("/delete-shift/<shift_id>", methods=["POST"])
@manager_required
def delete_shift(shift_id):
    shift = mongo.db.shifts.find_one({"_id": ObjectId(shift_id)})
    if not shift:
        flash("Shift not found.", "danger")
        return redirect(url_for("manager.manage_shifts"))
    
    user_id = shift.get("user_id")
    date_str = shift.get("date", "")
    
    # Delete the shift
    mongo.db.shifts.delete_one({"_id": ObjectId(shift_id)})
    
    # Notify user of shift deletion
    if user_id:
        mongo.db.notifications.insert_one({
            "user_id": user_id,
            "message": f"Your shift on {date_str} has been removed.",
            "created_at": datetime.utcnow(),
            "read": False,
        })
    
    flash("Shift deleted successfully.", "success")
    return redirect(url_for("manager.manage_shifts"))


# -----------------------------------------
# REASSIGN SHIFT
# -----------------------------------------
@manager_bp.route("/reassign-shift/<shift_id>", methods=["POST"])
@manager_required
def reassign_shift(shift_id):
    shift = mongo.db.shifts.find_one({"_id": ObjectId(shift_id)})
    if not shift:
        flash("Shift not found.", "danger")
        return redirect(url_for("manager.manage_shifts"))
    
    new_user_id = request.form.get("new_user_id")
    if not new_user_id:
        flash("Please select a user to reassign.", "danger")
        return redirect(url_for("manager.edit_shift", shift_id=shift_id))
    
    new_user_id = ObjectId(new_user_id)
    date_str = shift.get("date", "")
    old_user_id = shift.get("user_id")
    
    # Check for shift conflict with new user
    has_conflict, conflicting_shift = check_shift_conflict(str(new_user_id), date_str, exclude_shift_id=shift_id)
    
    if has_conflict:
        user = mongo.db.users.find_one({"_id": new_user_id})
        user_name = user["name"] if user else "Unknown"
        flash(f"Conflict: {user_name} already has a shift on {date_str}. Please choose a different user or date.", "danger")
        return redirect(url_for("manager.edit_shift", shift_id=shift_id))
    
    # Update shift with new user
    mongo.db.shifts.update_one(
        {"_id": ObjectId(shift_id)},
        {
            "$set": {
                "user_id": new_user_id,
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    # Notify old user
    if old_user_id:
        mongo.db.notifications.insert_one({
            "user_id": old_user_id,
            "message": f"Your shift on {date_str} has been reassigned to another member.",
            "created_at": datetime.utcnow(),
            "read": False,
        })
    
    # Notify new user
    mongo.db.notifications.insert_one({
        "user_id": new_user_id,
        "message": f"You have been assigned a shift on {date_str}.",
        "created_at": datetime.utcnow(),
        "read": False,
    })
    
    flash("Shift reassigned successfully.", "success")
    return redirect(url_for("manager.manage_shifts"))


@manager_bp.route("/change-requests", methods=["GET", "POST"])
@manager_required
def change_requests():
    if request.method == "POST":
        req_id = request.form.get("req_id")
        action = request.form.get("action")

        if not req_id or not action:
            flash("Invalid request.", "danger")
            return redirect(url_for("manager.change_requests"))

        req = mongo.db.shift_change_requests.find_one({"_id": ObjectId(req_id)})
        if not req:
            flash("Request not found.", "danger")
            return redirect(url_for("manager.change_requests"))

        if action == "approve":
            # Update the shift
            mongo.db.shifts.update_one(
                {"date": req["date"], "user_id": req["user_id"]},
                {
                    "$set": {
                        "shift_code": req["requested_shift"],
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            # Update request status
            mongo.db.shift_change_requests.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "approved", "updated_at": datetime.utcnow()}},
            )

            # Notify user
            mongo.db.notifications.insert_one(
                {
                    "user_id": req["user_id"],
                    "message": f"Your shift change request for {req['date']} has been approved.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                }
            )

            flash("Request approved and shift updated.", "success")
        elif action == "reject":
            mongo.db.shift_change_requests.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "rejected", "updated_at": datetime.utcnow()}},
            )

            # Notify user
            mongo.db.notifications.insert_one(
                {
                    "user_id": req["user_id"],
                    "message": f"Your shift change request for {req['date']} has been rejected.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                }
            )

            flash("Request rejected.", "info")

        return redirect(url_for("manager.change_requests"))

    requests = list(mongo.db.shift_change_requests.find().sort("created_at", -1))
    users_map = {str(u["_id"]): u["name"] for u in mongo.db.users.find()}

    return render_template(
        "manager/change_requests.html",
        requests=requests,
        users_map=users_map,
    )


@manager_bp.route("/swap-requests", methods=["GET", "POST"])
@manager_required
def swap_requests():
    if request.method == "POST":
        req_id = request.form.get("req_id")
        action = request.form.get("action")

        if not req_id or not action:
            flash("Invalid request.", "danger")
            return redirect(url_for("manager.swap_requests"))

        req = mongo.db.shift_swap_requests.find_one({"_id": ObjectId(req_id)})
        if not req:
            flash("Request not found.", "danger")
            return redirect(url_for("manager.swap_requests"))

        if action == "approve":
            requester_shift = mongo.db.shifts.find_one(
                {"date": req["date"], "user_id": req["requester_id"]}
            )
            target_shift = mongo.db.shifts.find_one(
                {"date": req["date"], "user_id": req["target_user_id"]}
            )

            if requester_shift and target_shift:
                requester_shift_code = requester_shift.get("shift_code")
                target_shift_code = target_shift.get("shift_code")

                mongo.db.shifts.update_one(
                    {"_id": requester_shift["_id"]},
                    {
                        "$set": {
                            "shift_code": target_shift_code,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )
                mongo.db.shifts.update_one(
                    {"_id": target_shift["_id"]},
                    {
                        "$set": {
                            "shift_code": requester_shift_code,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )

            mongo.db.shift_swap_requests.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "approved", "updated_at": datetime.utcnow()}},
            )

            mongo.db.notifications.insert_one(
                {
                    "user_id": req["requester_id"],
                    "message": f"Your shift swap request for {req['date']} has been approved.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                }
            )
            mongo.db.notifications.insert_one(
                {
                    "user_id": req["target_user_id"],
                    "message": f"Your shift swap request for {req['date']} has been approved.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                }
            )

            flash("Request approved and shifts swapped.", "success")
        elif action == "reject":
            mongo.db.shift_swap_requests.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "rejected", "updated_at": datetime.utcnow()}},
            )

            mongo.db.notifications.insert_one(
                {
                    "user_id": req["requester_id"],
                    "message": f"Your shift swap request for {req['date']} has been rejected.",
                    "created_at": datetime.utcnow(),
                    "read": False,
                }
            )

            flash("Request rejected.", "info")

        return redirect(url_for("manager.swap_requests"))

    requests = list(mongo.db.shift_swap_requests.find().sort("created_at", -1))
    users_map = {str(u["_id"]): u["name"] for u in mongo.db.users.find()}

    return render_template(
        "manager/swap_requests.html",
        requests=requests,
        users_map=users_map,
    )
