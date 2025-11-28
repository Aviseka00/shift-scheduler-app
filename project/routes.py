from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from bson.objectid import ObjectId
from datetime import datetime
from extensions import mongo

project_bp = Blueprint("project", __name__)


def manager_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "manager":
            flash("Manager access required.", "danger")
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated


# SAME SHIFT TIMINGS AS MANAGER
SHIFT_TIMINGS = {
    "A": ("06:00", "14:30"),  # 6 AM → 2:30 PM
    "B": ("14:00", "22:30"),  # 2 PM → 10:30 PM
    "C": ("22:00", "06:00"),  # 10 PM → 6 AM next day
    "G": ("09:00", "17:30"),  # 9 AM → 5:30 PM
}


# -----------------------------------------
# LIST ALL PROJECTS
# -----------------------------------------
@project_bp.route("/", endpoint="list_projects")
@manager_required
def list_projects():
    projects = mongo.db.projects.find().sort("created_at", -1)
    projects = list(projects)
    return render_template("project/list_projects.html", projects=projects)


# -----------------------------------------
# CREATE NEW PROJECT
# -----------------------------------------
@project_bp.route("/create", methods=["GET", "POST"], endpoint="create_project")
@manager_required
def create_project():
    if request.method == "POST":
        name = request.form.get("name")
        desc = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        mongo.db.projects.insert_one({
            "name": name,
            "description": desc,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": datetime.utcnow()
        })

        flash("Project created!", "success")
        return redirect(url_for("project.list_projects"))

    return render_template("project/create_project.html")


# -----------------------------------------
# VIEW PROJECT
# -----------------------------------------
@project_bp.route("/view/<project_id>", endpoint="view_project")
@login_required
def view_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Project not found.", "danger")
        if session.get("role") == "manager":
            return redirect(url_for("project.list_projects"))
        return redirect(url_for("member.dashboard"))
    
    tasks = list(mongo.db.project_tasks.find({"project_id": ObjectId(project_id)}))
    shifts = list(mongo.db.shifts.find({"project_id": ObjectId(project_id)}).sort("date", 1))
    
    users_map = {str(u["_id"]): u["name"] for u in mongo.db.users.find()}
    
    is_manager = session.get("role") == "manager"
    
    return render_template(
        "project/view_project.html",
        project=project,
        tasks=tasks,
        shifts=shifts,
        users_map=users_map,
        is_manager=is_manager
    )


# -----------------------------------------
# EDIT PROJECT
# -----------------------------------------
@project_bp.route("/edit/<project_id>", methods=["GET", "POST"], endpoint="edit_project")
@manager_required
def edit_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for("project.list_projects"))
    
    if request.method == "POST":
        name = request.form.get("name")
        desc = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        mongo.db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "name": name,
                    "description": desc,
                    "start_date": start_date,
                    "end_date": end_date,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        flash("Project updated!", "success")
        return redirect(url_for("project.view_project", project_id=project_id))
    
    return render_template("project/edit_project.html", project=project)


# -----------------------------------------
# ADD TASK TO PROJECT
# -----------------------------------------
@project_bp.route("/add-task/<project_id>", methods=["GET", "POST"], endpoint="add_task")
@manager_required
def add_task(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for("project.list_projects"))
    
    if request.method == "POST":
        task_name = request.form.get("task_name")
        assigned_to = request.form.get("assigned_to")
        due_date = request.form.get("due_date")
        
        mongo.db.project_tasks.insert_one({
            "project_id": ObjectId(project_id),
            "task_name": task_name,
            "assigned_to": ObjectId(assigned_to),
            "due_date": due_date,
            "created_at": datetime.utcnow()
        })
        
        flash("Task added successfully!", "success")
        return redirect(url_for("project.view_project", project_id=project_id))
    
    users = list(mongo.db.users.find({"role": "member"}))
    return render_template("project/add_task.html", project=project, users=users)


# -----------------------------------------
# ADD SHIFT TO PROJECT (AUTO TIME)
# -----------------------------------------
@project_bp.route("/add-shift/<project_id>", methods=["GET", "POST"], endpoint="add_shift")
@manager_required
def add_shift(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for("project.list_projects"))
    
    if request.method == "POST":
        date_str = request.form.get("date")
        user_id = request.form.get("user_id")
        shift_code = request.form.get("shift_code")
        task = request.form.get("task") or ""

        if not date_str or not user_id or not shift_code:
            flash("Please fill all required fields.", "danger")
            users = list(mongo.db.users.find({"role": "member"}))
            return render_template("project/add_shift.html", project=project, users=users)

        # AUTO TIME from shift code
        start_time, end_time = SHIFT_TIMINGS.get(shift_code, ("09:00", "17:00"))
        
        # Check for shift conflict
        existing_shift = mongo.db.shifts.find_one({
            "date": date_str,
            "user_id": ObjectId(user_id)
        })
        
        if existing_shift:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            user_name = user["name"] if user else "Unknown"
            flash(
                f"Conflict: {user_name} already has a shift on {date_str}. "
                f"Please choose a different date or user.",
                "danger"
            )
            users = list(mongo.db.users.find({"role": "member"}))
            return render_template("project/add_shift.html", project=project, users=users)
        
        # Create new shift
        mongo.db.shifts.insert_one({
            "project_id": ObjectId(project_id),
            "date": date_str,
            "user_id": ObjectId(user_id),
            "shift_code": shift_code,
            "start_time": start_time,
            "end_time": end_time,
            "task": task,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        flash("Shift added successfully!", "success")
        return redirect(url_for("project.view_project", project_id=project_id))
    
    users = list(mongo.db.users.find({"role": "member"}))
    return render_template("project/add_shift.html", project=project, users=users)


# -----------------------------------------
# DELETE PROJECT
# -----------------------------------------
@project_bp.route("/delete/<project_id>", methods=["POST"], endpoint="delete_project")
@manager_required
def delete_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for("project.list_projects"))
    
    mongo.db.project_tasks.delete_many({"project_id": ObjectId(project_id)})
    
    mongo.db.shifts.update_many(
        {"project_id": ObjectId(project_id)},
        {"$set": {"project_id": None}}
    )
    
    mongo.db.projects.delete_one({"_id": ObjectId(project_id)})
    
    flash(f"Project '{project['name']}' deleted successfully!", "success")
    return redirect(url_for("project.list_projects"))
