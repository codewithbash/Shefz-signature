# SHEFz Signature

Phase 1 starter: Flask app factory, Blueprints, homepage and 404 page.

## Run it (Windows PowerShell)
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python run.py

Open http://127.0.0.1:5000

Edit `.env` first: set DATABASE_URL (create an empty `shefz_signature` database in phpMyAdmin) and your WhatsApp number.
The homepage does not use the database yet, so it also runs before MySQL is set up.

## Tailwind CSS (build on your own computer)
Needs Node.js (https://nodejs.org). In the project folder:

    npm install
    npm run build:css      # makes app/static/css/output.css
    npm run watch:css      # rebuilds automatically while you work

If `output.css` does not exist, the site falls back to `style.css`, so nothing breaks.
Rebuild `output.css` before every deployment and upload it (shared hosting has no Node).

## Phases 6-7: cart, checkout, orders, settings
After copying these files over your project:

    flask --app run init-db      # creates the new tables (orders, order_items, settings). Safe to repeat.
    npm run build:css            # rebuild output.css (new styles were added)
    python run.py

Then log in as admin, open **Admin > Settings** and enter the bank details and WhatsApp number.
Flow: add to cart -> log in -> checkout -> order saved -> order page shows bank details + "Send payment proof on WhatsApp"
-> admin marks it Paid and moves it through Confirmed / In production / Ready / Delivered.

## Final features
    flask --app run init-db      # adds the new user_addresses table
    npm run build:css

Email: leave MAIL_SERVER empty in `.env` while testing; emails (including password-reset links) print in the terminal.
On the live host, create a mailbox and fill in the MAIL_* values in `.env`.
