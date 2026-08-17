# TrackGuard — Vehicle Tracker Installation Scheduling System

**"Secure Your Vehicle. Track Your Journey."**

TrackGuard is a full-stack Django web application that lets customers book GPS vehicle
tracker installation appointments online, and lets TrackGuard staff manage services,
appointment slots, and bookings from a dedicated dashboard. It was built as a university
Software Engineering project and is a fully functional, runnable Django application —
not a static prototype.

---

## Features

**Customers can:**
- Register an account and log in / log out securely
- View available tracker installation services
- View available appointment dates and time slots
- Book an installation through a guided 4-step wizard (service → date → time slot → vehicle & confirm)
- Add and manage their own vehicles
- View, track the status of, and cancel their bookings
- Receive a unique booking reference on confirmation

**Administrators / staff can:**
- Log in to a dedicated staff dashboard with scheduling statistics
- View all bookings, customers, and vehicles
- Create, edit, delete, and toggle availability of appointment time slots
- Confirm, reject, or otherwise update the status of any booking
- Create, edit, and deactivate/delete tracker installation services
- View detailed customer records

---

## Technologies

- Python 3.12
- Django 5.0
- Django ORM & built-in authentication system
- Django Templates + Bootstrap 5 (via CDN)
- SQLite (development database)
- Graphviz (UML diagram generation for the project documentation)
- ReportLab (PDF documentation generation)

---

## Project Structure

```text
TrackGuard/
│
├── manage.py
├── trackguard/                  # Project settings, URLs, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── bookings/                    # Main application
│   ├── migrations/
│   ├── management/commands/seed_data.py
│   ├── templates/bookings/
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── tests.py
│
├── templates/base.html          # Shared site-wide base template
├── static/css/trackguard.css    # Custom styling on top of Bootstrap 5
│
├── documentation/                              # Academic documentation
│   ├── TrackGuard_Project_Documentation.pdf    # Combined PDF (all sections below)
│   ├── build_pdf.py                            # Script that generates the PDF
│   ├── user_stories.md
│   ├── use_case_diagram.png / .puml
│   ├── use_case_description.md
│   ├── sequence_diagram.png / .puml
│   ├── sequence_description.md
│   ├── class_diagram.png / .puml
│   └── class_diagram_description.md
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Installation & Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run database migrations

```bash
python manage.py migrate
```

### 4. Seed demo data (recommended)

Creates a demo admin account, a demo customer account, sample services, two weeks of
appointment slots, an example vehicle, and an example booking.

```bash
python manage.py seed_data
```

### 5. (Optional) Create your own superuser

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** in your browser.

### 7. Run the test suite

```bash
python manage.py test
```

All 15 tests (authentication, booking validation, authorization, and model behaviour)
should pass.

---

## Demo Credentials

After running `python manage.py seed_data`:

| Role       | Username   | Password           |
|------------|------------|---------------------|
| Admin/Staff | `admin`    | `AdminPass123!`     |
| Customer    | `customer` | `CustomerPass123!`  |

These are **demo credentials only** — never use them in a production deployment.
The Django admin site is available at `/admin/` using the same admin credentials.

---

## Key Booking Rules Enforced by the System

1. Customers cannot book a slot marked unavailable.
2. Customers cannot book a slot that is already at capacity.
3. Customers cannot select a date in the past (enforced in both the slot-creation form
   and the booking flow).
4. Vehicle information is validated server-side (registration number uniqueness, a
   realistic vehicle year).
5. A database-level partial unique constraint prevents a customer from holding two
   simultaneously active bookings on the same slot.
6. Cancelling a booking automatically frees the slot back up for other customers.
7. Every confirmed booking gets a unique, auto-generated booking reference (e.g. `TG-8F3A1C2B`).
8. Booking creation uses `transaction.atomic()` with `select_for_update()` row locking
   to minimise race-condition double-booking under concurrent requests.
9. Only authenticated users can create a booking (`@login_required`).
10. Customers can only view/cancel their own bookings; attempting to access another
    customer's booking redirects with an error message.
11. Staff (`is_staff=True`) can view and manage all bookings, customers, and vehicles.

---

## Screenshots

_Add screenshots of the Home page, Booking wizard, Customer Dashboard, and Staff
Dashboard here once you have run the project locally._

- `docs/screenshots/home.png`
- `docs/screenshots/booking-wizard.png`
- `docs/screenshots/customer-dashboard.png`
- `docs/screenshots/staff-dashboard.png`

---

## Academic Documentation

The `documentation/` folder contains everything required for the academic submission:

- **User Stories** — `user_stories.md`, also included in the main PDF
- **Use Case Diagram** — `use_case_diagram.png` (rendered with Graphviz) and
  `use_case_diagram.puml` (source), with a full written description in
  `use_case_description.md`
- **Sequence Diagram** — `sequence_diagram.png` / `.puml`, showing the main booking flow
  plus the "slot no longer available" alternate flow, described in
  `sequence_description.md`
- **Class Diagram** — `class_diagram.png` / `.puml`, matching the actual Django models
  in `bookings/models.py`, described in `class_diagram_description.md`
- **`TrackGuard_Project_Documentation.pdf`** — a single combined PDF containing a cover
  page (with placeholders for your name/registration number), table of contents,
  introduction, project overview, user stories, all three diagrams with descriptions,
  system features, and a conclusion. Regenerate it at any time with:

  ```bash
  pip install reportlab graphviz
  python documentation/build_pdf.py
  ```

  Before submitting, open the PDF and replace the `[STUDENT NAME]`,
  `[REGISTRATION NUMBER]`, `[DEPARTMENT]`, `[COURSE]`, `[LECTURER]`, `[INSTITUTION]`,
  and `[DATE]` placeholders on the cover page with your own details.

---

## License

This project was created for academic purposes as part of a university Software
Engineering course.
