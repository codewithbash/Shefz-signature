from urllib.parse import urlparse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.auth.forms import RegisterForm, LoginForm, ForgotForm, ResetForm, ProfileForm
from app.mailer import send_email
from app.extensions import db
from app.models import User, UserAddress


def safe_next(target):
    """Only allow redirects to paths on this site."""
    if target and not urlparse(target).netloc and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.account"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(full_name=form.full_name.data.strip(),
                    email=form.email.data.lower().strip(),
                    phone=form.phone.data.strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to SHEFz Signature. Your account is ready.", "success")
        return redirect(safe_next(request.args.get("next")) or url_for("auth.account"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.account"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.active and user.check_password(form.password.data):
            login_user(user)
            return redirect(safe_next(request.args.get("next")) or url_for("auth.account"))
        flash("Email or password is not correct.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You are logged out.", "success")
    return redirect(url_for("main.home"))


@bp.route("/account")
@login_required
def account():
    return render_template("auth/account.html")


@bp.route("/account/edit", methods=["GET", "POST"])
@login_required
def edit_account():
    saved = current_user.saved_address
    form = ProfileForm()
    if request.method == "GET":
        form.full_name.data = current_user.full_name
        form.phone.data = current_user.phone
        form.address.data = saved.address if saved else ""
        form.city.data = saved.city if saved else ""
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip()
        address, city = (form.address.data or "").strip(), (form.city.data or "").strip()
        if address or city:
            if saved is None:
                saved = UserAddress(user_id=current_user.id)
                db.session.add(saved)
            saved.address, saved.city = address, city
        elif saved is not None:
            db.session.delete(saved)
        db.session.commit()
        flash("Your details are saved.", "success")
        return redirect(url_for("auth.account"))
    return render_template("auth/edit_account.html", form=form)


# ---------------------------------------------------------- password reset
def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.active:
            # The token includes part of the current password hash, so it stops
            # working as soon as the password changes (one use only).
            token = _serializer().dumps({"id": user.id, "h": user.password_hash[-12:]})
            link = url_for("auth.reset", token=token, _external=True)
            send_email(user.email, "Reset your SHEFz Signature password",
                       f"Hello {user.full_name},\n\nUse this link to choose a new password. "
                       f"It works for 1 hour:\n{link}\n\nIf you did not ask for this, ignore this email.\n\nSHEFz Signature")
        # Same message either way, so nobody can test which emails have accounts.
        flash("If that email has an account, a reset link is on its way.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot.html", form=form)


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    try:
        data = _serializer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        flash("That reset link is invalid or has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot"))
    user = db.session.get(User, data.get("id", 0))
    if user is None or not user.active or user.password_hash[-12:] != data.get("h"):
        flash("That reset link is invalid or has already been used.", "error")
        return redirect(url_for("auth.forgot"))
    form = ResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Password changed. You can log in now.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset.html", form=form)
