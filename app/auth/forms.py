from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from app.models import User


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Phone (WhatsApp)", validators=[DataRequired(), Length(min=7, max=30)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class ForgotForm(FlaskForm):
    email = StringField("Your account email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send reset link")


class ResetForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    submit = SubmitField("Save new password")


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone (WhatsApp)", validators=[DataRequired(), Length(min=7, max=30)])
    address = TextAreaField("Delivery address", validators=[Optional(), Length(max=500)])
    city = StringField("City / State", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Save changes")
