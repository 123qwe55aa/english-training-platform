from django.test import TestCase
from courses.models import Course, Lesson, LessonMaterial, Session

class LearnerPagesTests(TestCase):
    def test_public_pages_include_accessible_meter_and_reward_dialog(self):
        for url in ['/', '/lessons/', '/progress/', '/recordings/']:
            response=self.client.get(url)
            self.assertContains(response,'data-learner-meter')
            self.assertContains(response,'role="progressbar"')
            self.assertContains(response,'data-learner-dialog')
            self.assertContains(response,'rewards.mjs')
            self.assertContains(response,'此设备')

    def test_video_and_dialogue_tasks_have_stable_distinct_ids(self):
        course=Course.objects.create(title='VOA',published=True)
        from courses.models import Student
        Student.objects.get(slug='learner').courses.add(course)
        lesson=Lesson.objects.create(course=course,number=11,title='Neighborhood',published=True)
        LessonMaterial.objects.create(lesson=lesson,published=True,data={'assets':{'main':{'title':'Main','file':'voa/lesson-11/main.mp4'},'quiz1':{'title':'Q1','file':'voa/lesson-11/q1.mp4'}},'videos':['main'],'transcript':['Anna: Hi.'],'quiz':[{'number':1,'question':'Where?','options':['A','B'],'answer':0,'media':['quiz1']}]})
        response=self.client.get(f'/materials/{lesson.pk}/')
        self.assertContains(response,'data-learner-video="video:main"')
        self.assertContains(response,'data-learner-video="video:quiz1"')
        self.assertContains(response,f'data-learner-dialogue="dialogue:lesson-{lesson.pk}"')
        session=Session.objects.create(number=6,title='整合练习',published=True)
        response=self.client.get(f'/sessions/{session.pk}/')
        self.assertContains(response,f'data-learner-dialogue="dialogue:session-{session.pk}"')

    def test_published_classroom_replay_also_has_a_video_reward(self):
        from courses.models import Recording
        recording=Recording.objects.create(title='Class replay',file='recordings/test.mp4',published=True,consent_confirmed=True)
        response=self.client.get(f'/recordings/{recording.pk}/')
        self.assertContains(response,f'data-learner-video="video:recording-{recording.pk}"')
