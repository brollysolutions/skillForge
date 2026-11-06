# API reference

See [current team, batch, and email-only API changes](team-batches.md#api-additions). These replace the former password/invitation flow.

Base URL: `/api/`. All endpoints require `Authorization: Bearer <access-token>` unless marked public. JSON request/response bodies are used except file upload (multipart) and downloads (PDF/CSV/original document).

Collection endpoints use `page` and `page_size` (default 20, maximum 100) and return `{count,next,previous,results}`. Detail endpoints return objects. Errors use a `detail` message or field-error mapping. Typical statuses: 400 validation, 401 unauthenticated, 403 wrong role, 404 inaccessible object, 409 conflict/dependency, 429 throttle, 503 external provider unavailable. No private media directory is publicly served.

## Authentication and people

| Method and path | Role | Request / behavior |
| --- | --- | --- |
| GET `health/` | Public | Service liveness; no sensitive configuration |
| POST `auth/login/` | Public | `{email}` → `{access,refresh,user}` |
| POST `auth/token/refresh/` | Public | `{refresh}` → rotated access/refresh pair; old refresh blacklisted |
| POST `auth/logout/` | Signed in | `{refresh}` belonging to current user; blacklists it; 204 |
| GET/PATCH `auth/profile/` | Signed in | Own profile; patch only `name`, `bio` |
| GET `admin/students/` | Admin, sales, trainer | All students for managers, own/batch students for trainers; `search` matches name/email |
| POST `admin/students/` | Admin, sales, trainer | `{name,email}`; grants active email-only access without sending mail; returns `{student,detail}`. |
| GET/PATCH `admin/students/{id}/` | Admin, sales, trainer | Read accessible student; patch `name`, `bio`, `is_active` |

There is no public signup. Staff approve personal email addresses. Email-only login does not verify ownership; anyone who knows an approved email can access that account.

## Courses, topics, materials

| Method and path | Role | Request / behavior |
| --- | --- | --- |
| GET/POST `courses/` | Trainer | List/search own courses; create `{title,description,is_active}` |
| GET/PUT/PATCH/DELETE `courses/{id}/` | Trainer | CRUD; dependent records prevent deletion |
| GET/POST `courses/{id}/enrollments/` | Trainer | List active enrollments; add `{student_ids:[1,2]}` |
| GET/POST `topics/` | Trainer | Filter `course`; create `{course,title,description,learning_objectives,difficulty}` |
| GET/PUT/PATCH/DELETE `topics/{id}/` | Trainer | CRUD with course ownership validation |
| GET/POST `materials/` | Trainer | List/filter `course`; create material with file or notes |
| POST `materials/upload/` | Trainer | Multipart: `file` (PDF, DOCX, TXT, PPTX, PY, IPYNB), `title`, `course`, optional `topic` and educational fields; notebook v4 cell sources only, no code execution |
| POST `materials/text/` | Trainer | `{title,course,topic?,notes,subject?,description?,learning_objectives?,important_concepts?,trainer_instructions?}` |
| GET/PATCH/DELETE `materials/{id}/` | Trainer | Read/edit private content; edits invalidate previous analysis approval |
| GET `materials/{id}/download/` | Trainer | Authenticated original-file download |
| POST `materials/{id}/analyze/` | Trainer | Groq chunk analysis; returns unapproved analysis |
| POST `materials/{id}/approve/` | Trainer | Optional `{analysis:{summary,topics,concepts,objectives,terminology}}`; validate and approve |

## Assignments and AI generation

| Method and path | Role | Request / behavior |
| --- | --- | --- |
| GET `assignments/` | Signed in | Trainer-owned or student-assigned; filters `search`, `course`, `topic`, `status` |
| POST `assignments/` | Trainer | Create draft using assignment payload below |
| GET `assignments/{id}/` | Signed in | Role-specific serializer; student questions visible only after starting an attempt |
| PUT/PATCH `assignments/{id}/` | Trainer | Edit draft; published content is immutable |
| DELETE `assignments/{id}/` | Trainer | Delete draft only |
| POST `assignments/{id}/publish/` | Trainer | Validate every question, explicitly approve and publish |
| POST `assignments/{id}/assign-students/` | Trainer | `{student_ids:[1,2]}` OR explicit `{all_enrolled:true}` |
| GET/POST `assignments/{id}/access/` | Trainer | List assignment access; update `{student_id,is_active}` |
| POST `assignments/{id}/close/` | Trainer | Stop new attempts and answer editing |
| POST `assignments/{id}/archive/` | Trainer | Remove from student assignment lists while preserving history |
| POST `assignments/{id}/release-results/` | Trainer | Requires closed/deadline-passed assessment and no pending submitted/grading work |
| POST `assignments/{id}/start/` | Student | Creates or resumes timed attempt; returns submission |
| POST `ai/generate-assignment/` | Trainer | Groq generates and validates draft; never auto-publishes |
| POST `ai/assignments/{id}/regenerate-question/` | Trainer | `{question_id}`; replaces one saved draft question and returns updated draft |

Assignment payload:

```json
{
  "title": "Python functions",
  "course": 1,
  "topic": 1,
  "description": "Practice input, output and functions.",
  "difficulty": "medium",
  "duration_minutes": 60,
  "attempts_allowed": 2,
  "passing_percentage": 50,
  "starts_at": null,
  "deadline": "2027-01-01T12:00:00Z",
  "questions": [{
    "type": "mcq",
    "title": "Function definition",
    "prompt": "Which keyword defines a Python function?",
    "marks": 10,
    "options": ["def", "class"],
    "correct_answer": ["def"],
    "explanation": "The def statement defines a function."
  }]
}
```

Question types: `mcq`, `multiple_select`, `fill_blank`, `short_answer`, `descriptive`, `coding`, `debugging`, `output_prediction`, `scenario`, `genai_practical`, `project`. Written/practical/project questions require `rubric`. New coding/debugging tasks use one visible `test_cases` record, each `{input,expected_output,is_hidden,weight}`; additional fields are `constraints`, `input_format`, `output_format`, `starter_code`, `language` (Python only). New manual and generated assignments use one task and one output check. Legacy assessments remain readable and gradable.

Generation uses assignment configuration plus `material?`, `number_of_questions`, `question_types`, `total_marks`, `learning_objectives?`, `instructions?`. Supply material, a topic, or detailed manual instructions. Response is a saved draft assignment. Invalid counts, types, marks, answer structures or test cases prevent saving.

## Attempts, execution, evaluation

| Method and path | Role | Request / behavior |
| --- | --- | --- |
| GET `submissions/` | Signed in | Own student attempts or trainer-owned assessment submissions; filter `assignment`, `status`, trainer-only `student` |
| GET `submissions/{id}/` | Signed in | Submission with responses; unreleased marks/feedback are omitted for students |
| POST `submissions/{id}/save/` | Student owner | `{answers:{"question_id":"answer"}}`; multiple-select answer is a string array |
| POST `submissions/{id}/submit/` | Student owner | Optional `answers` saved before finalization; after expiry send `{}` to grade previously saved answers only |
| POST `submissions/{id}/review/` | Trainer owner | `{response_id,score,feedback}`; validates mark bounds, appends evaluation audit, recomputes totals |
| POST `submissions/{id}/ai-review/` | Trainer owner | `{response_id}`; stores qualitative Groq suggestion; does not change official marks |
| POST `code/run/` | Student owner | `{submission_id,question_id,code,input?}`; absent input runs sample tests; custom input runs once |

Final code grading happens through the same submission endpoint as all other question types. There is intentionally no independent final-code endpoint that could bypass assessment timers/attempt limits. Code run results include status, stdout, stderr, compilation output, time and memory, bounded by the executor. Final grading exposes only aggregate hidden-test success and sample execution details after result release.

## Reports, recommendations, analytics

| Method and path | Role | Request / behavior |
| --- | --- | --- |
| POST `reports/generate/{student_id}/` | Trainer | Generate Gemini report from own student's released, evaluated history |
| GET/POST `reports/batch/` | Trainer | List the latest twenty batch reports or generate a Gemini learning-gap analysis from aggregate evidence |
| GET `reports/batch/{id}/download/` | Trainer | Download own classroom analysis as PDF |
| GET `reports/` | Signed in | Trainer-owned or student-owned published reports; trainer can filter `student` |
| GET `reports/{id}/` | Signed in | Report snapshot; trainer-only observations redacted for students |
| POST `reports/{id}/publish/` | Trainer | Publish report; create student notification once |
| POST `reports/{id}/recommendations/` | Trainer | `{enabled:true/false}`; toggle learning-path visibility |
| GET `reports/{id}/download/` | Signed in | Authorized PDF with verified metrics and permitted narrative |
| GET `student/learning-path/` | Student | Latest published report's enabled recommendations, with currently accessible real assignment links |
| GET `admin/dashboard/` | Trainer | Database-driven classroom metrics, charts, deadlines, recent events, student summary |
| GET `student/dashboard/` | Signed in | Authenticated user's role-scoped dashboard |
| GET `student/performance/` | Signed in | Same role-scoped analytics |
| GET `analytics/overview/` | Signed in | Students always use self; admin/sales/trainers can filter `batch`, `course`, `topic`, `student`, `assignment`, `date_from`, `date_to` |
| GET `analytics/student/{id}/` | Trainer | Own student analytics |
| GET `analytics/course/{id}/` | Trainer | Own course analytics |
| GET `analytics/assignment/{id}/` | Trainer | Own assessment analytics |
| GET `analytics/export/` | Trainer | Same filters; CSV by default, `format=pdf` for PDF |
| GET `leaderboard/` | Signed in | Configurable classroom ranking; `period=week` for rolling seven days, otherwise overall |
| GET `notifications/`, `notifications/{id}/` | Signed in | Only current user's notifications |
| POST `notifications/{id}/read/` | Signed in | Mark own notification as read |
| GET/PATCH `settings/` | Trainer | Organization name, leaderboard/recommendation visibility; GET includes configured-service booleans and recent usage metadata |

Aliases: `student/assignments/`, `student/submissions/`, and `student/reports/` reuse the same identity-scoped collection handlers. Public-facing UI uses the canonical endpoints above.

Numeric metrics are never accepted from frontend request bodies. Report generation sends no student email/name to Gemini. Operational model choices and keys are environment settings, not editable browser fields.
