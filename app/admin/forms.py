from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, IntegerField,
                     SelectField, BooleanField, SubmitField)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, ValidationError


class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired(), Length(max=150)])
    category_id = SelectField("Category", coerce=int)
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    price = DecimalField("Price (₦)", places=2, validators=[DataRequired(), NumberRange(min=0)])
    availability_type = SelectField("How is it sold?", choices=[
        ("made_to_order", "Made to order"), ("ready_made", "Ready-made (already made)")])
    production_days = IntegerField("Making time (days after payment)", validators=[Optional(), NumberRange(min=1, max=365)])
    express_available = BooleanField("Offer express making")
    express_days = IntegerField("Express making time (days)", validators=[Optional(), NumberRange(min=1, max=365)])
    express_fee = DecimalField("Express fee (₦)", places=2, validators=[Optional(), NumberRange(min=0)])
    stock_status = SelectField("Status", choices=[
        ("available", "Available"), ("sold_out", "Sold out"), ("unavailable", "Temporarily unavailable")])
    stock_quantity = IntegerField("Quantity in stock (ready-made only)", validators=[Optional(), NumberRange(min=0)])
    sizes = StringField("Sizes (separate with commas)", validators=[Optional(), Length(max=200)])
    colours = StringField("Colours (separate with commas)", validators=[Optional(), Length(max=200)])
    is_featured = BooleanField("Show on the homepage")
    is_active = BooleanField("Visible in the shop")
    submit = SubmitField("Save product")

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if not ok:
            return False
        if self.availability_type.data == "made_to_order":
            if not self.production_days.data:
                self.production_days.errors.append("Enter the making time in days.")
                ok = False
            if self.express_available.data:
                if not self.express_days.data:
                    self.express_days.errors.append("Enter the express making time.")
                    ok = False
                elif self.production_days.data and self.express_days.data >= self.production_days.data:
                    self.express_days.errors.append("Express must be faster than standard.")
                    ok = False
                if self.express_fee.data is None:
                    self.express_fee.errors.append("Enter the express fee.")
                    ok = False
        return ok


class SettingsForm(FlaskForm):
    bank_name = StringField("Bank name", validators=[Optional(), Length(max=80)])
    account_number = StringField("Account number", validators=[Optional(), Length(max=20)])
    account_name = StringField("Account name", validators=[Optional(), Length(max=120)])
    whatsapp_number = StringField("WhatsApp number (e.g. 08087234718)", validators=[DataRequired(), Length(max=30)])
    payment_note = TextAreaField("Extra payment instruction (optional)", validators=[Optional(), Length(max=300)])
    notification_email = StringField("Email for new-order alerts", validators=[Optional(), Email(), Length(max=120)])
    instagram_url = StringField("Instagram link", validators=[Optional(), Length(max=200)])
    tiktok_url = StringField("TikTok link", validators=[Optional(), Length(max=200)])
    facebook_url = StringField("Facebook link", validators=[Optional(), Length(max=200)])
    x_url = StringField("X (Twitter) link", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Save settings")

    def _check_url(self, field):
        from app.settings_service import normalise_url
        if normalise_url(field.data) is None:
            raise ValidationError("Enter a valid web address, for example instagram.com/yourpage.")

    def validate_instagram_url(self, field): self._check_url(field)
    def validate_tiktok_url(self, field): self._check_url(field)
    def validate_facebook_url(self, field): self._check_url(field)
    def validate_x_url(self, field): self._check_url(field)

    def validate_whatsapp_number(self, field):
        from app.settings_service import normalise_whatsapp
        if not normalise_whatsapp(field.data):
            raise ValidationError("Enter a valid phone number, for example 08087234718.")
