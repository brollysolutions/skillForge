# Python Practice: 10 Individual Questions

Create ONE assignment containing TEN separate questions. Each question has its own editor, code, expected output, check, and 10 marks. The total is 100 marks. Suggested duration: 120 minutes. Set your course, batch, and deadline.

## Enter the questions

1. Open Assignments > Manual assignment and enter the title "Python Practice: 10 Individual Questions".
2. Fill Question 1 with its title, problem statement, starter code, and expected output below. Select Coding and set 10 marks.
3. Click Add question and fill Question 2. Repeat until Question 10. Do not put all ten statements into one question.
4. Leave Input data (stdin) empty for EVERY question. All data is provided as Python variables in its starter code.
5. Save draft & preview, check that the preview contains 10 separate questions and 100 total marks, then publish. Use Assign students if no batch was selected.

Alternatively, upload questions/01.txt into Question 1's upload field, questions/02.txt into Question 2's upload field, and so on. Copy each matching starter-code and expected-output file into that question's fields. Uploading a question file fills only the problem statement.

## Student workflow

Students answer one question at a time, choose Check question, and use Next to continue. Each matched question is marked Completed. Completed progress is saved and restored on reopening. Editing a passed answer requires checking it again. Once all 10 pass, the assignment completes automatically. Students may also submit partial work for individual question marks; official scores follow the trainer's release process.

These questions use topics from your Python basics, primitive types, collection types, and transformation notebooks. Each expected output was independently verified. There are no shared variables between questions, no Q1/Q2 output headings, and no combined output to paste.

## Question 1: Notebook purchase total

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

A notebook costs 45 rupees. A student buys 6 notebooks. Calculate and print the total cost using the supplied variables. Print only the number.

**Python starter code**

```python
price = 45
quantity = 6

# Write your solution below.
```

**Expected output**

```text
270
```

## Question 2: Add tax to a product price

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

A product costs 1000 rupees before tax. Add 5% tax and print the final price as a float. Calculate from the supplied variables. Print only the final price.

**Python starter code**

```python
price = 1000
tax_percent = 5

# Write your solution below.
```

**Expected output**

```text
1050.0
```

## Question 3: Clean a course name

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

Remove spaces from both ends of the supplied course name. Convert it to lowercase and print the cleaned name. Keep the space between the two words.

**Python starter code**

```python
course_name = '  pYtHon bAsIcS  '

# Write your solution below.
```

**Expected output**

```text
python basics
```

## Question 4: First and last cities

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

Using indexing, print the first city and then the last city in the supplied list. Print each city on a separate line, without quotes or labels.

**Python starter code**

```python
cities = ['Hyderabad', 'Pune', 'Chennai', 'Delhi']

# Write your solution below.
```

**Expected output**

```text
Hyderabad
Delhi
```

## Question 5: Every second value

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

Use list slicing to select every second value, starting with the first value in the supplied list. Print the resulting list on one line.

**Python starter code**

```python
numbers = [12, 24, 36, 48, 60, 72]

# Write your solution below.
```

**Expected output**

```text
[12, 36, 60]
```

## Question 6: Update a tuple record

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

The tuple fields are ID, name, and salary. Convert the tuple to a list, change the name to anil kumar, and increase the salary by 5000. Convert the result back to a tuple and print it. Keep the ID unchanged.

**Python starter code**

```python
student = (201, 'anil', 50000)

# Write your solution below.
```

**Expected output**

```text
(201, 'anil kumar', 55000)
```

## Question 7: Update student marks

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

Increase Ravi's marks by 5. Add Kiran with 90 marks. Keep the other marks unchanged and print the updated dictionary. Update the existing dictionary so that the original key order is preserved and Kiran appears last.

**Python starter code**

```python
marks = {'Asha': 65, 'Ravi': 80, 'Meena': 75}

# Write your solution below.
```

**Expected output**

```text
{'Asha': 65, 'Ravi': 85, 'Meena': 75, 'Kiran': 90}
```

## Question 8: Count unique students

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Easy

**Problem statement**

Convert the supplied list of student IDs to a set to remove duplicates. Print the number of unique student IDs. Print only the count, not the set.

**Python starter code**

```python
student_ids = [11, 12, 11, 13, 14, 12, 14]

# Write your solution below.
```

**Expected output**

```text
4
```

## Question 9: Increase all salaries

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Medium

**Problem statement**

Increase every salary in the supplied list by the fixed increment of 3000. Use a for loop or list comprehension. Keep the original order and print the updated list with integer values.

**Python starter code**

```python
salaries = [15000, 22000, 30000]
increment = 3000

# Write your solution below.
```

**Expected output**

```text
[18000, 25000, 33000]
```

## Question 10: Find above-average marks

**Question type:** Coding | **Marks:** 10 | **Difficulty:** Medium

**Problem statement**

Calculate the average of the supplied marks using sum() and len(). Select marks strictly greater than the average, preserving their original order. Print the average on the first line and the selected list on the second line. Do not include marks equal to the average.

**Python starter code**

```python
marks = [50, 60, 70, 80, 90]

# Write your solution below.
```

**Expected output**

```text
70.0
[80, 90]
```
