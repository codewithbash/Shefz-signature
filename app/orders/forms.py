import re
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class CheckoutForm(FlaskForm):
    customer_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone number (WhatsApp if possible)", validators=[DataRequired(), Length(max=30)])
    delivery_address = TextAreaField("Delivery address", validators=[DataRequired(), Length(max=500)])
    city = StringField("City / State", validators=[DataRequired(), Length(max=80)])
    notes = TextAreaField("Anything we should know? (optional)", validators=[Optional(), Length(max=500)])
    save_details = BooleanField("Save these delivery details for next time", default=True)
    submit = SubmitField("Place order")

    def validate_phone(self, field):
        digits = re.sub(r"\D", "", field.data or "")
        if not 7 <= len(digits) <= 15:
            raise ValidationError("Enter a valid phone number.")
