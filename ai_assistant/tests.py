from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from grades.models import Grade, Subject
from students.models import Classroom, Student

from .services.ai_tools import ai_actions, data_service


class ReadOnlyAIToolsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='x')
        self.other_teacher = User.objects.create_user(username='other', password='x')

        self.classroom = Classroom.objects.create(
            teacher=self.teacher,
            name='Decimo A',
            grade_level='10',
        )
        other_classroom = Classroom.objects.create(
            teacher=self.other_teacher,
            name='Once B',
            grade_level='11',
        )

        self.student = Student.objects.create(
            teacher=self.teacher,
            classroom=self.classroom,
            first_name='Juan',
            last_name='Perez',
            active=True,
        )
        Student.objects.create(
            teacher=self.other_teacher,
            classroom=other_classroom,
            first_name='Ana',
            last_name='Gomez',
            active=True,
        )

        self.subject = Subject.objects.create(name='Matematicas', active=True)
        Grade.objects.create(
            student=self.student,
            subject=self.subject,
            activity_name='Quiz 1',
            score=4.5,
            max_score=5,
            date=date(2026, 1, 15),
        )

    def test_count_students_is_scoped_to_teacher(self):
        result = data_service.count_students(self.teacher)

        self.assertEqual(result['count'], 1)

    def test_student_grades_returns_only_accessible_records(self):
        result = data_service.student_grades(self.teacher, 'Juan Perez', 'Matematicas')

        self.assertTrue(result['found'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['grades'][0]['score'], 4.5)

    def test_execute_validated_action(self):
        action = ai_actions.AIAction(
            name='student_average',
            params={'student': 'Juan Perez', 'subject': 'Matematicas'},
        )

        result = ai_actions.execute_action(self.teacher, action)

        self.assertEqual(result['action'], 'student_average')
        self.assertEqual(result['result']['average'], 4.5)

    def test_detect_action_rejects_unknown_action(self):
        class FakeProvider:
            def chat(self, *args, **kwargs):
                return '{"action":"drop_table","params":{}}'

        self.assertIsNone(ai_actions.detect_action(FakeProvider(), 'borra estudiantes'))

    def test_detect_action_accepts_known_action(self):
        class FakeProvider:
            def chat(self, *args, **kwargs):
                return '{"action":"count_students","params":{"grade":"10"}}'

        action = ai_actions.detect_action(FakeProvider(), 'cuantos estudiantes hay en decimo')

        self.assertEqual(action.name, 'count_students')
        self.assertEqual(action.params['grade'], '10')
