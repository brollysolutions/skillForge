# Database and scoring

All models use Django ORM types compatible with PostgreSQL. Committed initial migrations define the custom user model before any dependent foreign key.

| Domain | Models | Main relationships and constraints |
| --- | --- | --- |
| Accounts | User, Invitation | Case-insensitive unique email; student → trainer; invitation hashes unique, expiring, single-use |
| Curriculum | Course, Topic, CourseEnrollment | Course → trainer; topic → course; unique course/student enrollment |
| Content | StudyMaterial | Course/topic ownership; private UUID file path; original filename/size, extracted text, analysis and approval |
| Assessments | Assignment, Question, TestCase, AssignmentAccess | Question → assignment; test → question; unique assignment/student access |
| Work | Submission, QuestionResponse | Unique assignment/student/attempt and submission/question; timer and finalization state |
| Evaluation | Evaluation | Immutable review history: response, reviewer, previous/new Decimal score, feedback |
| Reports | PerformanceReport, LearningRecommendation, BatchReport | Student/trainer ownership; metrics/evidence/narrative snapshot; publication; real topic/assignment links; trainer-private aggregate batch reports |
| Operations | AuditLog, Notification, AIUsageLog, PlatformSettings | Actor-scoped events, private notifications, provider usage/errors, per-trainer configuration |

## Numeric rules

- Marks and scores use `DecimalField`, rounded to two decimal places. Assignment total marks are the sum of validated question marks.
- MCQ: full marks for the one stored correct option, otherwise zero.
- Multiple select, exact policy: full marks only for an exact correct option set.
- Multiple select, partial policy: `marks × max(0, correct selections − incorrect selections) / number of correct options`.
- Fill-in/output prediction: Unicode NFKC normalization, case-folding, and whitespace normalization, compared against explicit accepted answers.
- Coding/debugging: `marks × sum(passed test weights) / sum(all test weights)`. Sample and hidden tests both contribute. Output comparison ignores only trailing whitespace; other content must match.
- Unanswered questions receive zero. Nonempty written/practical/project answers remain pending until a trainer reviews them.
- Submission percentage: `100 × awarded marks / assignment total marks`.
- Analytics and points use the best evaluated result per student/assessment so repeat attempts do not inflate totals. Student analytics include only released results. Completion counts submitted or evaluated distinct student/assessment pairs among active assigned records.
- Average score is the arithmetic mean of these best result percentages, not a marks-weighted cross-assessment average.
- Topic averages group those percentages by assessment topic. A mixed-topic assessment should be split into separate assessments if question-level topic attribution is needed.

## Retention and migrations

Dependent curriculum and assessed question records use `PROTECT` to preserve history. Draft questions can be replaced because drafts cannot have student attempts. Archive published assignments instead of deleting them.

Back up `backend/db.sqlite3` together with private uploaded materials. Migrate to PostgreSQL by changing Django database settings, installing a supported PostgreSQL adapter, migrating an empty target database, and transferring data with a reviewed export/import procedure. Review collation, email uniqueness, sequences and concurrent-attempt tests after transfer. JSON fields contain provider schema data, options, answer variants and bounded execution summaries; core relational ownership and access are foreign keys.
