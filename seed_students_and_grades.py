import random
from datetime import date
from django.contrib.auth.models import User
from students.models import Student, Classroom
from grades.models import Grade, Subject

random.seed(99)

teacher = User.objects.first()
subjects = list(Subject.objects.all())

STUDENTS_11A = [
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

STUDENTS_NEW = {
    "1A": [
        ("ALARCON MESA", "LUIS MIGUEL", "1085301001", "M"),
        ("BERNAL CASTRO", "SARA VALENTINA", "1085301002", "F"),
        ("CAICEDO RENDON", "ANDRES FELIPE", "1085301003", "M"),
        ("DAVILA OSPINA", "MARIA FERNANDA", "1085301004", "F"),
        ("ESCOBAR LOZANO", "JUAN CAMILO", "1085301005", "M"),
        ("FLOREZ VARGAS", "LAURA MILENA", "1085301006", "F"),
        ("GUTIERREZ PENA", "CARLOS MARIO", "1085301007", "M"),
        ("HERRERA SOTO", "DANIELA ALEJANDRA", "1085301008", "F"),
        ("IBARRA MONTOYA", "SEBASTIAN", "1085301009", "M"),
        ("JIMENEZ RIOS", "VALENTINA", "1085301010", "F"),
    ],
    "1B": [
        ("LONDONO CANO", "MIGUEL ANGEL", "1085401001", "M"),
        ("MARIN ZAPATA", "ISABELLA", "1085401002", "F"),
        ("NARVAEZ HOYOS", "DAVID ESTEBAN", "1085401003", "M"),
        ("ORTEGA SALCEDO", "MANUELA", "1085401004", "F"),
        ("PALACIOS VELEZ", "SANTIAGO", "1085401005", "M"),
        ("QUINTANA BEDOYA", "LUISA FERNANDA", "1085401006", "F"),
        ("RENDON AGUDELO", "NICOLAS", "1085401007", "M"),
        ("SALAZAR GARCIA", "ANA SOFIA", "1085401008", "F"),
        ("TORRES MENDEZ", "JUAN PABLO", "1085401009", "M"),
        ("URIBE CASTANO", "CAMILA", "1085401010", "F"),
    ],
    "2A": [
        ("VARGAS MEJIA", "PEDRO PABLO", "1085501001", "M"),
        ("WATERHOUSE LEON", "SOFIA ELENA", "1085501002", "F"),
        ("YEPES CARDONA", "MATEO", "1085501003", "M"),
        ("ZAMORA CUESTA", "VALERIA", "1085501004", "F"),
        ("ACEVEDO FRANCO", "JULIAN", "1085501005", "M"),
        ("BECERRA SILVA", "NATALIA", "1085501006", "F"),
        ("CIFUENTES MORA", "SAMUEL", "1085501007", "M"),
        ("DIAZ BERMUDEZ", "PAULA ANDREA", "1085501008", "F"),
        ("ESTRADA MARIN", "TOMAS", "1085501009", "M"),
        ("FUENTES ARANGO", "MELISSA", "1085501010", "F"),
    ],
    "2B": [
        ("GALVIS PEREZ", "SIMON", "1085601001", "M"),
        ("HENAO ZULUAGA", "MARIANA", "1085601002", "F"),
        ("ISAZA CORTEZ", "ALEJANDRO", "1085601003", "M"),
        ("JARAMILLO BUITRAGO", "SALOME", "1085601004", "F"),
        ("LOPEZ RESTREPO", "GABRIEL", "1085601005", "M"),
        ("MOLINA SANCHEZ", "EMILY", "1085601006", "F"),
        ("NARANJO GOMEZ", "IVAN", "1085601007", "M"),
        ("OROZCO VILLA", "TATIANA", "1085601008", "F"),
        ("POSADA DUQUE", "RAFAEL", "1085601009", "M"),
        ("RIOS VELASQUEZ", "CAROLINA", "1085601010", "F"),
    ],
}

ACTIVITIES = [
    ("Taller 1", "activity", "Periodo 1", date(2025, 2, 14)),
    ("Quiz 1", "quiz", "Periodo 1", date(2025, 2, 28)),
    ("Examen P1", "exam", "Periodo 1", date(2025, 3, 21)),
    ("Proyecto P1", "project", "Periodo 1", date(2025, 4, 4)),
    ("Participacion", "participation", "Periodo 1", date(2025, 4, 11)),
    ("Taller 2", "activity", "Periodo 2", date(2025, 4, 25)),
    ("Quiz 2", "quiz", "Periodo 2", date(2025, 5, 2)),
    ("Examen P2", "exam", "Periodo 2", date(2025, 5, 30)),
]


def create_grades(student, subjects):
    base = random.uniform(2.8, 5.0)
    for subj in subjects:
        for act_name, act_type, period, act_date in ACTIVITIES:
            if Grade.objects.filter(student=student, subject=subj, activity_name=act_name).exists():
                continue
            score = round(min(5.0, max(1.0, base + random.uniform(-1.0, 0.6))), 1)
            Grade.objects.create(
                student=student,
                subject=subj,
                subject_text=subj.name,
                activity_name=act_name,
                grade_type=act_type,
                score=score,
                max_score=5.0,
                period=period,
                date=act_date,
                observations="",
            )


total_students = 0
total_grades = 0

# 11A
cr_11a = Classroom.objects.filter(name="11A").first()
if cr_11a:
    for last_name, first_name, doc, gender in STUDENTS_11A:
        st, created = Student.objects.get_or_create(
            document_id=doc,
            defaults={
                "teacher": teacher,
                "classroom": cr_11a,
                "last_name": last_name,
                "first_name": first_name,
                "gender": gender,
                "active": True,
            },
        )
        if created:
            total_students += 1
        if subjects:
            before = Grade.objects.filter(student=st).count()
            create_grades(st, subjects)
            total_grades += Grade.objects.filter(student=st).count() - before
    print("11A processed:", len(STUDENTS_11A), "students")
else:
    print("11A not found, skipping")

# New classrooms
for cr_name, rows in STUDENTS_NEW.items():
    cr, _ = Classroom.objects.get_or_create(
        name=cr_name,
        defaults={"teacher": teacher, "grade_level": cr_name[:-1], "subject": ""},
    )
    for last_name, first_name, doc, gender in rows:
        st, created = Student.objects.get_or_create(
            document_id=doc,
            defaults={
                "teacher": teacher,
                "classroom": cr,
                "last_name": last_name,
                "first_name": first_name,
                "gender": gender,
                "active": True,
            },
        )
        if created:
            total_students += 1
        if subjects:
            before = Grade.objects.filter(student=st).count()
            create_grades(st, subjects)
            total_grades += Grade.objects.filter(student=st).count() - before
    print(cr_name, "processed:", len(rows), "students")

print("Total students created:", total_students)
print("Total grades created:", total_grades)
print("Total students in DB:", Student.objects.count())
print("Total grades in DB:", Grade.objects.count())