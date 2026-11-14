# Python assignments with expected output

Trainers create one assignment containing up to 10 separate questions. Each question has its own instructions, input data, starter code, expected output, and marks. Students write Python in the active question editor and choose **Check question** (or **Check & complete** for a single-question assignment). The server runs the saved code through the configured isolated runner. A matching output completes that question; all Python questions passing completes the assignment; an incorrect output or Python error leaves the same attempt open for editing until its time limit or deadline. A runner outage also preserves the student's code for retry.

## Create the salary assignment

1. Open **Assignments → Manual assignment**, choose a course and optionally a batch, and set the duration and deadline.
2. Keep the question type as **Coding**. Choose **Use salary increment example** to fill the question, input, starter comments, and expected output. All these fields remain editable.
3. Use this task: “Write a Python program to increase every student's salary by 10%. Read the student count, then one name and salary per line. Print each name and increased salary in the original order, with two decimal places. Do not print prompts or extra messages.”
4. Provide **Input data (stdin)**:

   ```text
   3
   Asha 20000
   Ravi 30000
   Meena 25000
   ```

5. Provide **Expected output**:

   ```text
   Asha 22000.00
   Ravi 33000.00
   Meena 27500.00
   ```

6. To add another independent question, choose **Add question** and fill its own fields. Repeat up to 10 questions. See the [ready-to-enter practice set](python-practice-10-questions.md). Save the draft, review the preview, and publish. Batch members receive access automatically; for an unbatched assignment, use **Assign students**.

The **Problem statement** can also be imported from PDF, DOCX, or TXT. Enter input data and expected output separately after importing. **Input format** describes how to read the data; **Input data (stdin)** supplies the actual values to Python's `input()` function. If no input is needed, leave input data empty.

## Student experience

- Start the assignment to see its instructions, input, expected output, and Python editor.
- **Run sample tests** compares output without submitting. **Run custom input** runs with the student's own input and does not count as completion.
- **Check question** saves the answers and checks only the selected question against its expected output. A mismatch displays expected and actual output together, with any Python errors. The student can fix the code and try again within the same timed attempt.
- A match saves the question evaluation and shows its completed badge. Use Next or the numbered navigation to continue. Progress survives reloading. Editing a passed answer clears its completion until it is checked again. When every Python question passes, the assignment is submitted and locked automatically. Students may also submit partial work; marks are summed per question. Official scores and private explanations still follow the existing trainer release process.
- After time expires, the student can submit the code already saved on the server using the existing submission flow.

Matching is case-sensitive and preserves line order and internal spacing. Whitespace at the end of the entire output is ignored. An output match verifies the supplied check; it does not assess how the algorithm was written.

Python execution requires a reachable [Piston](piston-setup.md) or Judge0 runner. Student code is never executed by the Django process.

## API

`POST /api/submissions/{id}/check-complete/` accepts `question_id` and the same `answers` mapping as save/submit. The question ID can be omitted only for a single-question assignment. It checks that coding or debugging question and returns `question_id`, `question_completed`, assignment-level `completed`, visible `results`, and `submission`. Each serialized response includes `question_completed`. The server evaluates all configured checks, including hidden checks on older tasks, and only returns visible outputs. A successful retry does not execute code twice. The assignment stays `in_progress` while questions remain incomplete. When all coding questions pass, it uses the existing `evaluated` status with `task_completed: true` in the submission API. Mixed-type assignments use normal submission and review for non-coding questions.
