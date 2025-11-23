from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import mongo

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email").lower()
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        role = request.form.get("role")
        manager_key = request.form.get("manager_key")
        
        # Get selected projects (for members only)
        project_ids = request.form.getlist("project_ids")  # Can be multiple

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        # Manager secret key check
        if role == "manager":
            SECRET_MANAGER_KEY = "ADMIN2025"  # 🔒 change this in real deployment
            if manager_key != SECRET_MANAGER_KEY:
                flash("Invalid Manager Secret Key!", "danger")
                return redirect(url_for("auth.register"))

        if mongo.db.users.find_one({"email": email}):
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))

        password_hash = generate_password_hash(password)

        user_doc = {
            "name": name,
            "email": email,
            "phone": phone,
            "password_hash": password_hash,
            "role": role,  # "member" or "manager"
            "created_at": datetime.utcnow(),
        }
        
        # Add project associations for members only
        if role == "member" and project_ids:
            from bson.objectid import ObjectId
            user_doc["project_ids"] = [ObjectId(pid) for pid in project_ids]

        mongo.db.users.insert_one(user_doc)

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("auth.login"))

    # GET request - load projects for selection
    from bson.objectid import ObjectId
    projects = list(mongo.db.projects.find().sort("name", 1))
    return render_template("auth/register.html", projects=projects)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").lower()
        password = request.form.get("password")

        user = mongo.db.users.find_one({"email": email})
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        session["user_id"] = str(user["_id"])
        session["role"] = user["role"]
        session["name"] = user["name"]

        flash("Logged in successfully.", "success")
        if user["role"] == "manager":
            return redirect(url_for("manager.dashboard"))
        else:
            return redirect(url_for("member.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


