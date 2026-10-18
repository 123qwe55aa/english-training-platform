from django.db import migrations

def preserve(apps,schema_editor):
    Student=apps.get_model('courses','Student')
    Course=apps.get_model('courses','Course')
    student,_=Student.objects.get_or_create(slug='jason',defaults={'name':'Jason','published':True,'planned_sessions':168,'planned_lessons':52,'schedule':'每晚 20:00—21:00'})
    if not student.schedule:
        student.schedule='每晚 20:00—21:00'
        student.save(update_fields=['schedule'])
    student.courses.add(*Course.objects.values_list('pk',flat=True))

class Migration(migrations.Migration):
    dependencies=[('courses','0003_alter_lesson_options_alter_lesson_number_and_more')]
    operations=[migrations.RunPython(preserve,migrations.RunPython.noop)]
