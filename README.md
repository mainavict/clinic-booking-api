# Clinic Booking System API

An asynchronous REST API for a clinic booking system, built with FastAPI, SQLAlchemy (async), and PostgreSQL (Neon). 

This system is designed to handle concurrent medical bookings securely, enforce complex operational constraints (like staff lunch breaks), and scale gracefully as the clinic grows.

## Live Application & Submission Links
- **Public API URL**: https://clinic-booking-api-emay.onrender.com
- **Interactive Swagger Docs**: https://clinic-booking-api-emay.onrender.com/docs
- **GitHub Repository**: https://github.com/mainavict/clinic-booking-api

---

## SECTION 1: SYSTEM DESIGN

### Models and Components Identified
The system follows a Clean Architecture approach, separating concerns for maintainability and testability:
- **API Layer (Routers)**: Handles HTTP requests, Pydantic validation, and response formatting.
- **Service Layer**: Orchestrates complex business rules (30-min slots, future buffer, lunch constraints, concurrency checks).
- **Data Layer**: Async SQLAlchemy with PostgreSQL, utilizing connection pooling and pessimistic locking. **Database migrations are managed via Alembic**, ensuring safe, version-controlled schema evolution in production.
- **Core Models**: 
  - `Doctor`: Includes working hours, staggered lunch breaks, contact info, and secure password hashing.
  - `Patient`: Includes contact info and secure password hashing.
  - `Appointment`: Includes status, cancellation reasons, and strict time boundaries.

### Key Design Decisions & Trade-offs

1. **UUIDs over Auto-Incrementing Integers**: 
   - *Decision*: All primary and foreign keys use UUIDs.
   - *Trade-off*: Slightly larger index size, but prevents ID enumeration attacks (e.g., guessing `/appointments/1`) and makes future database sharding or distributed scaling trivial as the clinic grows.

2. **Dynamic Slot Generation vs. Pre-creation**: 
   - *Decision*: Slots are generated dynamically in the `GET /availability` endpoint rather than pre-creating DB rows for every day.
   - *Trade-off*: Pre-creation makes availability a simple `SELECT`, but bloats the database and requires cron jobs to clean up past slots. Dynamic generation keeps the DB lean and infinitely scalable.

3. **Concurrency & Race Conditions**:
   - *Decision*: Implemented **Pessimistic Locking** (`with_for_update()`) on the doctor's appointments during the booking transaction, combined with application-level overlap checks.
   - *Trade-off*: Pessimistic locking slightly reduces write throughput under extreme load, but guarantees 100% data integrity for medical bookings, which is far more critical than microsecond latency.

4. **Operational Constraints (The 25% Lunch Rule)**:
   - *Decision*: The clinic requires that no more than 25% of the staff can be on a lunch break simultaneously. Instead of hardcoding the "5 doctors" assumption from the prompt, the system dynamically counts the actual `COUNT(doctors)` in the database and calculates `int(total * 0.25)` on the fly. If a new doctor's lunch overlaps with the maximum allowed limit, the API rejects the schedule configuration.

5. **Configurable Business Rules**:
   - *Decision*: Externalized the maximum booking window (`MAX_DAYS_IN_ADVANCE`) and minimum advance booking time (`MIN_HOURS_IN_ADVANCE`) to environment variables via Pydantic Settings.
   - *Trade-off*: Allows the clinic's operations team to adjust scheduling policies (e.g., extending to 90 days during holiday seasons) without requiring a code deployment or risking regression bugs.

6. **Security & Authentication Readiness**:
   - *Decision*: Proactively added `hashed_password` fields to both Doctor and Patient models using `bcrypt` (via `passlib`). Passwords are hashed at the service layer before being persisted, and Pydantic response schemas explicitly exclude password fields to prevent accidental data leaks.

---

## SECTION 2: API IMPLEMENTATION

### Endpoints Implemented
- `POST /api/v1/appointments` — Book a slot. Validates working hours, future buffer, lunch breaks, and concurrency.
- `GET /api/v1/doctors/{doctor_id}/availability` — Returns all available 30-minute slots for a doctor on a given date.
- `PATCH /api/v1/appointments/{appointment_id}/cancel` — Cancels an appointment with a reason, freeing the slot.
- `PATCH /api/v1/appointments/{appointment_id}/reschedule` — Moves an appointment to a new slot atomically, validating the new slot and freeing the old one.
- `GET /api/v1/doctors/{doctor_id}/appointments` — Fetches upcoming appointments for a specific doctor with pagination.
- `GET /api/v1/patients/{patient_id}/appointments` — Upcoming appointments sorted by date, with offset/limit pagination for scalability.
- `GET /api/v1/patients` — Returns a paginated list of all patients (useful for admin dashboards).
- `POST /api/v1/doctors` & `POST /api/v1/patients` — For dynamic system setup and testing.

### Constraints & Validation
- Validation failures return meaningful error messages with correct HTTP status codes (e.g., `400 Bad Request`, `409 Conflict`, `422 Unprocessable Entity`) via Global Exception Handlers.
- Code is sensibly structured into `api`, `services`, `models`, `schemas`, and `core` directories.
- **Test Coverage**: Comprehensive test coverage for all endpoints and business logic edge cases is included in the `tests/` directory. Specifically, we test: health checks, invalid UUID handling, booking in the past, the future buffer, the advance limit, lunch break violations, double-booking conflicts (409), duplicate patient emails, and the dynamic 25% staffing lunch rule. I utilized `pytest` with service-layer mocking (`unittest.mock.patch`) to ensure the CI/CD pipeline runs the full suite in under 2 seconds without requiring a live database connection. *(Note: AI was instrumental in helping me structure these tests, particularly in setting up the dependency overrides and mock patches for fast, isolated execution).*

---

## SECTION 3: DEPLOYMENT & CI/CD

### Public URL & Deployment
- **Public URL**: https://clinic-booking-api-emay.onrender.com
- **Cloud Provider**: Render (using a production-optimized `Dockerfile`).
- **Database**: Neon (Serverless Postgres) for auto-scaling and branching capabilities.

### CI/CD Pipeline Setup
- **Branch Trigger**: The `main` branch triggers both testing and deployment.
- **Pipeline Description**: 
  - Located in `.github/workflows/ci-cd.yml`.
  - **On Pull Request**: The pipeline checks out the code, sets up Python 3.11, installs dependencies, provides dummy environment variables for Pydantic Settings validation, and runs the `pytest` suite to ensure booking logic and constraints hold.
  - **On Merge to `main`**: Once the tests pass and the PR is merged, the pipeline automatically triggers a deployment webhook (`RENDER_DEPLOY_HOOK`) to Render. Render then pulls the latest code, rebuilds the Docker container, and deploys the new version without manual intervention.

### Testing the CI/CD Pipeline
To verify the pipeline is working:
1. Create a feature branch and make changes
2. Open a Pull Request to `main`
3. GitHub Actions will automatically run the test suite
4. Green checkmarks ✅ indicate all tests passed
5. Merging to `main` triggers automatic deployment to Render

---

## SECTION 4: AI REFLECTION

**1. What did you use AI for across the four sections?**
- Brainstorming edge cases for timezone handling and daylight saving shifts.
- Generating boilerplate Pydantic schemas and the GitHub Actions CI/CD YAML.
- **Writing the comprehensive `pytest` test suite**, specifically helping me set up `unittest.mock.patch` and database dependency overrides to test complex business logic (like the 25% lunch rule and double-booking) in isolation without needing a live database.
- Structuring the README and reflection document for maximum clarity and professionalism.

**2. Give one example where an AI suggestion improved your work. What did you prompt it with?**
- *Prompt*: "How can I prevent race conditions when two users try to book the same 30-minute slot at the exact same millisecond in SQLAlchemy async?"
- *Improvement*: AI suggested using `with_for_update()` (pessimistic locking). I was initially going to rely solely on application-level checks, which would have failed under concurrent load. This suggestion made the system truly production-ready.

**3. Give one example where AI output was wrong or incomplete and how you caught it.**
- *Issue*: AI initially suggested cancelling the old appointment and creating a brand new one for the `reschedule` endpoint. 
- *How I caught it*: I realized this would break the advance-booking buffer rule for the *new* slot and could create orphaned records if the second step failed. I corrected it to update the existing appointment's `start_time` and `end_time` atomically within a single transaction, which inherently frees the old slot safely.

**4. Name three decisions you made without AI. Why did you trust your own judgment there?**
- **Decision 1: Using UUIDs instead of Auto-Incrementing Integers for Primary Keys.** AI initially suggested using standard auto-incrementing integers for IDs, as it is the default boilerplate. I overrode this because integers are predictable (posing an ID enumeration security risk, e.g., guessing `/appointments/1`) and do not scale well for distributed systems. I trusted my judgment to implement UUIDs to ensure the system is secure and highly scalable as the clinic grows.
- **Decision 2: Introducing Lunch Breaks and the 25% Staffing Rule.** AI initially modeled the doctors as having continuous, unbroken working hours (e.g., 9 AM to 5 PM straight). I overrode this because real-world clinics require doctors to take breaks. I designed the lunch break schema and the 25% concurrency rule (ensuring at least 75% of staff is always available). Furthermore, I implemented this rule as a dynamic database query rather than a static config, knowing clinics grow and hardcoding "1 out of 5 doctors" would create immediate technical debt.
- **Decision 3: Enforcing Strict Pagination on List Endpoints.** AI often generates simple `SELECT *` queries for list endpoints (like fetching all appointments or patients), which works fine for small datasets. I overrode this to enforce strict offset/limit pagination (`skip` and `limit` parameters) on all list endpoints. I trusted my judgment here because in a real-world clinical setting, a doctor or admin might have thousands of historical records. Fetching them all at once would cause memory exhaustion and severe API latency. Pagination guarantees the system remains highly scalable and responsive as the database grows.

---

## Future Enhancements (V2 Roadmap)
While the current system robustly handles the core booking lifecycle as an MVP, the following features are identified for future iterations as the clinic grows:
1. **Doctor Absence/Leave Management**: A dedicated `DoctorLeave` model and endpoints to mark doctors as absent on specific future dates. This would automatically block availability generation for those days and proactively notify affected patients, rather than relying on manual cancellations.
2. **Automated Patient Notifications**: Integration with an email/SMS service (e.g., Resend, Twilio) to send booking confirmations, cancellation alerts, and 24-hour reminders.
3. **Role-Based Access Control (RBAC)**: Implementing JWT authentication to distinguish between `Patient`, `Doctor`, and `Clinic Admin` roles, restricting who can cancel or view specific appointments.

---

## How to Run Locally

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/mainavict/clinic-booking-api
   cd clinic-booking-api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt