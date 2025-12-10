from datetime import datetime, timedelta
import os
import secrets
from werkzeug.utils import secure_filename

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import mongo
from bson.objectid import ObjectId

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    return ext in allowed_extensions


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
            return redirect("/manager/dashboard")
        else:
            return redirect("/member/dashboard")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password - requires privilege key for managers"""
    if request.method == "POST":
        email = request.form.get("email").lower()
        role = request.form.get("role")
        manager_key = request.form.get("manager_key", "")
        
        # Find user
        user = mongo.db.users.find_one({"email": email})
        if not user:
            # Don't reveal if email exists for security
            flash("If the email exists, a password reset link has been sent.", "info")
            return redirect(url_for("auth.login"))
        
        # Verify role matches
        if user.get("role") != role:
            flash("Invalid email or role combination.", "danger")
            return redirect(url_for("auth.forgot_password"))
        
        # Manager privilege key check
        if role == "manager":
            SECRET_MANAGER_KEY = "ADMIN2025"
            if manager_key != SECRET_MANAGER_KEY:
                flash("Invalid Manager Privilege Key! Managers must provide the correct key to reset password.", "danger")
                return redirect(url_for("auth.forgot_password"))
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
        
        # Store reset token
        mongo.db.password_reset_tokens.insert_one({
            "user_id": user["_id"],
            "email": email,
            "token": reset_token,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
            "used": False
        })
        
        # Generate reset URL
        reset_url = url_for("auth.reset_password", token=reset_token, _external=True)
        
        # Try to send email
        try:
            from utils.email_utils import send_email
            
            subject = "Password Reset Request - Shift Scheduler"
            email_body = f"""
Hello {user.get('name', 'User')},

You have requested to reset your password for your Shift Scheduler account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email. Your password will remain unchanged.

Best regards,
Shift Scheduler Team
"""
            
            email_sent = send_email(email, subject, email_body)
            
            if email_sent:
                flash("Password reset link has been sent to your email address. Please check your inbox.", "success")
                return redirect(url_for("auth.login"))
            else:
                # Email sending failed, show link as fallback
                flash("Email could not be sent. Please use this reset link:", "warning")
                flash(f"{reset_url}", "info")
                flash("Note: Configure email settings in Render.com environment variables to enable email sending.", "info")
                return redirect(url_for("auth.reset_password", token=reset_token))
                
        except Exception as e:
            # Email utility not available or error occurred
            current_app.logger.error(f"Email sending error: {str(e)}")
            flash("Email could not be sent. Please use this reset link:", "warning")
            flash(f"{reset_url}", "info")
            flash("Note: Configure email settings in Render.com environment variables to enable email sending.", "info")
            return redirect(url_for("auth.reset_password", token=reset_token))
    
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password using token"""
    # Find valid token
    reset_record = mongo.db.password_reset_tokens.find_one({
        "token": token,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not reset_record:
        flash("Invalid or expired reset token. Please request a new password reset.", "danger")
        return redirect(url_for("auth.forgot_password"))
    
    user = mongo.db.users.find_one({"_id": reset_record["user_id"]})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.forgot_password"))
    
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.reset_password", token=token))
        
        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for("auth.reset_password", token=token))
        
        # Update password
        password_hash = generate_password_hash(new_password)
        mongo.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"password_hash": password_hash}}
        )
        
        # Mark token as used
        mongo.db.password_reset_tokens.update_one(
            {"_id": reset_record["_id"]},
            {"$set": {"used": True, "used_at": datetime.utcnow()}}
        )
        
        flash("Password reset successfully! Please login with your new password.", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("auth/reset_password.html", token=token, email=user.get("email", ""))


@auth_bp.route("/upload-profile-picture", methods=["POST"])
def upload_profile_picture():
    """Unified endpoint for both manager and member to upload profile pictures"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    try:
        user_id = ObjectId(session["user_id"])
        user = mongo.db.users.find_one({"_id": user_id})
        
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Check if file was uploaded
        if "profile_picture" not in request.files:
            return jsonify({"success": False, "message": "No file provided"}), 400
        
        file = request.files["profile_picture"]
        
        # Check if file is empty
        if file.filename == "":
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Invalid file type. Only JPG, PNG, JPEG, or GIF allowed."}), 400
        
        # Get upload folder from config
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "static/uploads/profile_pics")
        
        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Get file extension and create secure filename
        file_ext = file.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(f"{user_id}.{file_ext}")
        filepath = os.path.join(upload_folder, filename)
        
        # Save file
        file.save(filepath)
        
        # Update user record
        mongo.db.users.update_one(
            {"_id": user_id},
            {"$set": {"profile_picture": filename}}
        )
        
        return jsonify({"success": True, "message": "Profile picture updated successfully!", "filename": filename})
    except Exception as e:
        import traceback
        error_msg = str(e)
        # Always return JSON, never HTML
        response = jsonify({"success": False, "message": f"Error uploading file: {error_msg}"})
        response.status_code = 500
        return response


