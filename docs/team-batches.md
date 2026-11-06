# Team and batch workflow

This update adds one admin, sales staff, trainers, and students. Existing trainer accounts and historical assessments are preserved.

## Access

- **Admin:** creates sales and trainer access, manages courses and batches, grants student access, and views all student performance.
- **Sales:** creates trainer and student access, assigns courses and batches, and views staff details and performance. Sales cannot create admins/sales users, generate or publish assignments, or edit marks.
- **Trainer:** manages their batches, adds students, creates/uploads or generates assignments, grades work, and releases results. A student can attend batches taught by different trainers. Each trainer sees only their own assessment results.
- **Student:** sees assigned work and their own released results.

Login accepts `{ "email": "approved@example.com" }`. Addresses are trimmed and normalized to lowercase. Only existing active accounts can sign in. No password, OTP, invitation, or login email is used, as requested. **This identifies an account but does not verify the person: anyone who knows an approved email can access that account, including staff accounts.** Role permissions still apply after sign-in. Deactivation invalidates access and refresh sessions, including after reactivation.

## First setup

Run migrations, then create the single admin using an email you control:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py bootstrap_admin admin@example.com --name "Platform Admin"
```

Replace the example address with the real admin email. The database permits at most one admin. `bootstrap_admin` refuses to overwrite an existing account. If exactly one legacy trainer has superuser status and no admin exists, migration promotes that account to admin. Other trainers are preserved. The admin can sign into the application with their email and add staff under **Team access**. There are no default admin credentials.

## Teaching workflow

1. Admin/sales adds trainers and students by name and personal email.
2. Create a course with its primary trainer. Create batches under that course, assigning a trainer to each batch. Trainers can see courses where they own the course or teach a batch.
3. Enroll students from the batch roster. This also enrolls them in its course. A batch can have many students and each trainer can have many batches.
4. In **Batches**, choose **Create / upload task** or **Generate with AI**. Task upload accepts PDF, DOCX, or TXT and imports its text for review (maximum 12,000 characters). Set one task, its marks, deadline, and attempt duration. For coding tasks, enter one visible input and expected output. AI generates one task only. Written/practical tasks use an explicit trainer-reviewed rubric.
5. Review and publish. Current active batch members receive access automatically. Enrolling later does not retroactively grant older work; use **Assign students** on an existing assignment. Archive prevents creating/publishing new batch work; existing assignments keep their lifecycle and can be closed individually.
6. Students submit before their deadline/attempt limit. Python runs on the configured isolated Piston/Judge0 service. Output comparison ignores trailing whitespace; errors and wrong outputs do not pass. No local execution fallback exists.
7. Close the task (or wait for its deadline), finish any written-answer reviews, then release results. Students can see the expected output beside their actual output, with matched/not-matched status. Dashboards show completion, scores, topic mastery, and output accuracy. Filter **Performance** by batch to compare that group's results.

Existing assessments with multiple questions/tests remain readable and gradable. Historical output records created before this update may lack stored expected-output text; the UI labels that explicitly.

## API additions

All paths below are relative to `/api/`.

| Endpoint | Purpose |
| --- | --- |
| `GET/POST staff/`, `PATCH staff/{id}/` | Admin/sales manage permitted staff roles |
| `GET/POST batches/`, `PATCH batches/{id}/` | Staff manage batches; trainers are restricted to their own |
| `GET/POST batches/{id}/members/` | Read roster or enroll `student_ids`; also grants course enrollment |
| `POST assignments/import-question/` | Trainer-only multipart `file`; returns extracted `prompt` |
| `POST assignments/` | Accepts optional `batch`; batch tasks require a deadline |
| `POST ai/generate-assignment/` | Accepts optional `batch`; `number_of_questions` must be 1 |
| `GET assignments/?batch={id}` | Filter assignments by batch |
| `GET analytics/overview/?batch={id}` | Staff-only filter, combined with existing course/student/date filters |

Password reset/change and invitation-acceptance routes are removed. `POST admin/students/` returns `student` and `detail`, without an initial password. `POST auth/login/` accepts email only. Token refresh/logout remain available.
