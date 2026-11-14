export function salaryExample() {
  return {
    type: 'coding', title: 'Increase every student salary by 10%',
    prompt: 'Write a Python program to increase the salary of every student by 10%.\nRead the student count, followed by one name and salary per line. Keep the original order. Print each name and the increased salary with exactly two decimal places, separated by one space. Do not print prompts or extra messages.\n\nFor example, a salary of 20000 becomes 22000.00 after a 10% increase.',
    difficulty: 'easy', marks: 10, options: [], correct_answer: [], explanation: '',
    rubric: '', marking_policy: 'exact', language: 'python',
    constraints: '1 to 100 students. Names contain no spaces. Salaries are non-negative whole numbers.',
    input_format: 'First line: number of students. Each following line: student_name salary.',
    output_format: 'One line per student: student_name new_salary. Format each new salary to two decimal places.',
    starter_code: '# Read the number of students.\n# For each student, read their name and salary.\n# Increase the salary by 10% and print the result.\n',
    test_cases: [{input: '3\nAsha 20000\nRavi 30000\nMeena 25000', expected_output: 'Asha 22000.00\nRavi 33000.00\nMeena 27500.00', is_hidden: false, weight: 1}],
  };
}
