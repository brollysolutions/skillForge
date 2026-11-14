# Python assignments with expected output

Trainers provide the task instructions, input data, and expected output. Students write Python in the assignment workspace and choose **Check & complete**. The server runs the saved code through the configured isolated runner. A matching output completes the task; an incorrect output or Python error leaves the same attempt open for editing until its time limit or deadline. A runner outage also preserves the student's code for retry.

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

6. Save the draft, review the preview, and publish. Batch members receive access automatically; for an unbatched assignment, use **Assign students**.

The **Problem statement** can also be imported from PDF, DOCX, or TXT. Enter input data and expected output separately after importing. **Input format** describes how to read the data; **Input data (stdin)** supplies the actual values to Python's `input()` function. If no input is needed, leave input data empty.

## Student experience

- Start the assignment to see its instructions, input, expected output, and Python editor.
- **Run sample tests** compares output without submitting. **Run custom input** runs with the student's own input and does not count as completion.
- **Check & complete** saves the current code and checks the trainer's expected output. A mismatch displays expected and actual output together, with any Python errors. The student can fix the code and try again within the same timed attempt.
- A match saves the evaluation, locks the submitted code, and shows **Completed** on the assignment and submission pages. Official scores and private explanations still follow the existing trainer release process.
- After time expires, the student can submit the code already saved on the server using the existing submission flow.

Matching is case-sensitive and preserves line order and internal spacing. Whitespace at the end of the entire output is ignored. An output match verifies the supplied check; it does not assess how the algorithm was written.

Python execution requires a reachable [Piston](piston-setup.md) or Judge0 runner. Student code is never executed by the Django process.

## API

`POST /api/submissions/{id}/check-complete/` accepts the same `answers` mapping as save/submit. It supports a single coding or debugging question and returns `completed`, visible `results`, and `submission`. The server evaluates all configured checks, including hidden checks on older tasks, and only returns visible outputs. A successful retry does not execute code twice. A failed check stays `in_progress`; success uses the existing `evaluated` status with `task_completed: true` in the submission API.
