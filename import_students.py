import random
from datetime import date

from django.contrib.auth.models import User
from students.models import Student, Classroom
from grades.models import Grade

# ==============================
# DOCENTE
# ==============================

teacher = User.objects.first()

if not teacher:
    raise Exception("No hay usuarios en la base de datos")

print("Docente:", teacher.username)

# ==============================
# SALON
# ==============================

classroom = Classroom.objects.filter(name="11A").first()

if not classroom:
    raise Exception("No existe el salon 11A")

print("Salon:", classroom.name)

# ==============================
# ESTUDIANTES
# ==============================

STUDENTS = [
    ("ACOSTA RIASCOS", "JUAN ESTEBAN", "1085201001", "M"),
    ("ANGULO OBANDO", "JUAN SEBASTIAN", "1085201002", "M"),
    ("ARANGO AVENDANO", "GABRIELA", "1085201003", "F"),
    ("ARBOLEDA DELGADO", "SOFIA", "1085201004", "F"),
    ("ATEHORTUA SANCHEZ", "ALEJANDRO", "1085201005", "M"),
    ("BARANDICA SANDOVAL", "JUAN JOSE", "1085201006", "M"),
    ("BONILLA ORTIZ", "CATALINA", "1085201007", "F"),
    ("CARO MARTINEZ", "DANIEL", "1085201008", "M"),
    ("CARRILLO BARRERA", "GABRIELA", "1085201009", "F"),
    ("CASTRILLON AGUIRRE", "ANA MARIA", "1085201010", "F"),
    ("CIFUENTES OBANDO", "LAURA SOFIA", "1085201011", "F"),
    ("CORREA GALEANO", "NICOLAS", "1085201012", "M"),
    ("DELGADO PERAFAN", "VALENTINA", "1085201013", "F"),
    ("GALARZA TOVAR", "SEBASTIAN", "1085201014", "M"),
    ("GARCIA DIAZ", "CARLOS ANDRES", "1085201015", "M"),
    ("GARCIA DIAZ", "VIOLETA", "1085201016", "F"),
    ("GIRALDO HERRERA", "MARIANA", "1085201017", "F"),
    ("GIRALDO PARRA", "MARIA GUADALUPE", "1085201018", "F"),
    ("GOMEZ LEAL", "JAVIER ALEJANDRO", "1085201019", "M"),
    ("GUERRERO PEREIRA", "MARIA JOSE", "1085201020", "F"),
    ("GUZMAN CASTRO", "MARIANA", "1085201021", "F"),
    ("MAHECHA CALA", "JHON DEYVID", "1085201022", "M"),
    ("MAMIAN SANCHEZ", "SANTIAGO", "1085201023", "M"),
    ("MORENO VASQUEZ", "ISABELLA", "1085201024", "F"),
    ("OCAMPO OCAMPO", "EMMANUEL", "1085201025", "M"),
    ("ORTIZ ESPITIA", "NICOLAS", "1085201026", "M"),
    ("PERDOMO CLAVIJO", "VALERIA", "1085201027", "F"),
    ("QUINONES GALINDO", "SARA", "1085201028", "F"),
    ("QUINTERO RIVERA", "JUAN DAVID", "1085201029", "M"),
    ("RAMIREZ TRUJILLO", "SABINA ALEXANDRA", "1085201030", "F"),
    ("RESTREPO GARCIA", "MARIANA", "1085201031", "F"),
    ("TREJOS COBO", "SEBASTIAN", "1085201032", "M"),
    ("URBANO NUNEZ", "MIGUEL ANGEL", "1085201033", "M"),
    ("VALENCIA CARDONA", "SOFIA", "1085201034", "F"),
    ("VIAFARA CANADAS", "HANNAH DANIELA", "1085201035", "F"),
]

# ==============================
# ACTIVIDADES
# ==============================

ACTIVITIES = [
    ("Taller", "activity"),
    ("Quiz", "quiz"),
    ("Parcial", "exam"),
    ("Proyecto", "project"),
]

# ==============================
# CREACION
# ==============================

created = 0

for last_name, first_name, doc, gender in STUDENTS:

    student, was_created = Student.objects.get_or_create(
        document_id=doc,
        defaults={
            "teacher": teacher,
            "classroom": classroom,
            "last_name": last_name,
            "first_name": first_name,
            "gender": gender,
            "active": True,
        }
    )

    if was_created:

        for activity_name, grade_type in ACTIVITIES:

            score = round(random.uniform(2.8, 5.0), 1)

            Grade.objects.create(
                student=student,
                activity_name=activity_name,
                grade_type=grade_type,
                score=score,
                max_score=5.0,
                period="Primer periodo",
                date=date.today(),
                observations=""
            )

        created += 1
        print("Creado:", first_name, last_name)

print()
print("TOTAL CREADOS:", created)