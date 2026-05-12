from grades.models import Grade
from students.models import Student

deleted_grades, _ = Grade.objects.all().delete()
deleted_students, _ = Student.objects.all().delete()

print("Grades deleted:", deleted_grades)
print("Students deleted:", deleted_students)
print("Users, Classrooms and Subjects preserved.")