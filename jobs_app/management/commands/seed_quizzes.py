from django.core.management.base import BaseCommand
from jobs_app.models import QuizModel, QuestionModel

class Command(BaseCommand):
    help = 'Seeds initial quizzes and questions for Python, DSA, and Aptitude categories.'

    def handle(self, *args, **options):
        # 1. Python Foundation Test
        python_quiz, created = QuizModel.objects.get_or_create(
            title="Python Foundation Test",
            category="python"
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created 'Python Foundation Test' quiz."))
        else:
            self.stdout.write("Quiz 'Python Foundation Test' already exists.")

        # Add questions for Python
        # Clear existing questions to prevent duplicates and ensure exactly 10 questions
        python_quiz.questions.all().delete()
        
        q_data_py = [
            {
                "text": "Which of the following is used to define a block of code in Python?",
                "option_a": "Parentheses",
                "option_b": "Curly braces",
                "option_c": "Indentation",
                "option_d": "Quotation marks",
                "correct_option": "C"
            },
            {
                "text": "What does the 'len()' function do in Python?",
                "option_a": "Returns the type of an object",
                "option_b": "Returns the number of items in an object",
                "option_c": "Converts an object to a string",
                "option_d": "Returns the memory size of an object",
                "correct_option": "B"
            },
            {
                "text": "Which python keyword is used to define a function?",
                "option_a": "func",
                "option_b": "def",
                "option_c": "function",
                "option_d": "define",
                "correct_option": "B"
            },
            {
                "text": "What is the output of the list comprehension: [x**2 for x in range(5) if x % 2 == 0]?",
                "option_a": "[0, 4, 16]",
                "option_b": "[0, 2, 4]",
                "option_c": "[4, 16]",
                "option_d": "[0, 1, 4, 9, 16]",
                "correct_option": "A"
            },
            {
                "text": "Which of the following Python data types is immutable?",
                "option_a": "List",
                "option_b": "Dictionary",
                "option_c": "Tuple",
                "option_d": "Set",
                "correct_option": "C"
            },
            {
                "text": "Given a = [1, 2] and b = [1, 2], what do 'a == b' and 'a is b' evaluate to respectively?",
                "option_a": "True, True",
                "option_b": "True, False",
                "option_c": "False, True",
                "option_d": "False, False",
                "correct_option": "B"
            },
            {
                "text": "What is the primary purpose of a decorator in Python?",
                "option_a": "To visually format source code",
                "option_b": "To modify or extend function behavior dynamically",
                "option_c": "To compile Python scripts to bytecode",
                "option_d": "To manage garbage collection",
                "correct_option": "B"
            },
            {
                "text": "In Python's variable scoping lookup, what does the LEGB rule stand for?",
                "option_a": "Local, Enclosing, Global, Built-in",
                "option_b": "List, Element, Group, Block",
                "option_c": "Lexical, Enclosed, General, Base",
                "option_d": "Local, External, Global, Bound",
                "correct_option": "A"
            },
            {
                "text": "What is the result of evaluating: (lambda x, y: x * y)(2, 3)?",
                "option_a": "5",
                "option_b": "6",
                "option_c": "8",
                "option_d": "9",
                "correct_option": "B"
            },
            {
                "text": "Which of the following types CANNOT be used as a dictionary key in Python?",
                "option_a": "String",
                "option_b": "Integer",
                "option_c": "List",
                "option_d": "Tuple containing only integers",
                "correct_option": "C"
            }
        ]

        for q in q_data_py:
            QuestionModel.objects.create(
                quiz=python_quiz,
                text=q["text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_option=q["correct_option"]
            )
            self.stdout.write(f"Added Python question: {q['text'][:40]}...")

        # 2. Data Structures Assessment
        dsa_quiz, created = QuizModel.objects.get_or_create(
            title="Data Structures Assessment",
            category="dsa"
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created 'Data Structures Assessment' quiz."))
        else:
            self.stdout.write("Quiz 'Data Structures Assessment' already exists.")

        # Add questions for DSA
        q_data_dsa = [
            {
                "text": "What is the time complexity of searching in a balanced binary search tree (BST)?",
                "option_a": "O(1)",
                "option_b": "O(N)",
                "option_c": "O(log N)",
                "option_d": "O(N log N)",
                "correct_option": "C"
            },
            {
                "text": "Which data structure operates on a Last In First Out (LIFO) basis?",
                "option_a": "Queue",
                "option_b": "Stack",
                "option_c": "Heap",
                "option_d": "Hash Table",
                "correct_option": "B"
            },
            {
                "text": "Which data structure is best suited for implementing a breadth-first search (BFS) on a graph?",
                "option_a": "Stack",
                "option_b": "Queue",
                "option_c": "Tree",
                "option_d": "Priority Queue",
                "correct_option": "B"
            }
        ]

        for q in q_data_dsa:
            question, q_created = QuestionModel.objects.get_or_create(
                quiz=dsa_quiz,
                text=q["text"],
                defaults={
                    "option_a": q["option_a"],
                    "option_b": q["option_b"],
                    "option_c": q["option_c"],
                    "option_d": q["option_d"],
                    "correct_option": q["correct_option"]
                }
            )
            if q_created:
                self.stdout.write(f"Added DSA question: {q['text'][:40]}...")

        # 3. Quantitative Aptitude Test
        aptitude_quiz, created = QuizModel.objects.get_or_create(
            title="Quantitative Aptitude Challenge",
            category="aptitude"
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created 'Quantitative Aptitude Challenge' quiz."))
        else:
            self.stdout.write("Quiz 'Quantitative Aptitude Challenge' already exists.")

        q_data_apt = [
            {
                "text": "If a car travels at a speed of 60 km/h, how far will it travel in 45 minutes?",
                "option_a": "45 km",
                "option_b": "50 km",
                "option_c": "40 km",
                "option_d": "55 km",
                "correct_option": "A"
            },
            {
                "text": "What is the average of first five prime numbers?",
                "option_a": "5.0",
                "option_b": "5.6",
                "option_c": "6.0",
                "option_d": "6.2",
                "correct_option": "B"
            }
        ]

        for q in q_data_apt:
            question, q_created = QuestionModel.objects.get_or_create(
                quiz=aptitude_quiz,
                text=q["text"],
                defaults={
                    "option_a": q["option_a"],
                    "option_b": q["option_b"],
                    "option_c": q["option_c"],
                    "option_d": q["option_d"],
                    "correct_option": q["correct_option"]
                }
            )
            if q_created:
                self.stdout.write(f"Added Aptitude question: {q['text'][:40]}...")

        self.stdout.write(self.style.SUCCESS("Successfully seeded initial quizzes!"))
