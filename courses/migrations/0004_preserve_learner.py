from django.db import migrations

def preserve(apps,schema_editor):
    Student=apps.get_model('courses','Student')
    Course=apps.get_model('courses','Course')
    student,_=Student.objects.get_or_create(slug='learner',defaults={'name':'Learner','published':True,'planned_sessions':24,'planned_lessons':12,'schedule':''})
    if not student.schedule:
        student.schedule=''
        student.save(update_fields=['schedule'])
    student.courses.add(*Course.objects.values_list('pk',flat=True))

class Migration(migrations.Migration):
    dependencies=[('courses','0003_alter_lesson_options_alter_lesson_number_and_more')]
    operations=[migrations.RunPython(preserve,migrations.RunPython.noop)]
