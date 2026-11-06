import os,sys,json
from pathlib import Path
from datetime import timedelta
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
os.environ['DJANGO_DB_PATH']=str(root/'.task-temp/browser.sqlite3')
import django
django.setup()
from django.utils import timezone
from accounts.models import User
from courses.models import Course
from assignments.models import Assignment,Question,AssignmentAccess
from submissions.models import Submission,QuestionResponse
from reports.models import PerformanceReport
trainer=User.objects.get(email='trainer@browser.test');student=User.objects.get(email='student@browser.test')
course,_=Course.objects.get_or_create(trainer=trainer,title='UI audit fixture')
assignment,_=Assignment.objects.update_or_create(trainer=trainer,course=course,title='UI audit: expected output',defaults={'status':'published','deadline':timezone.now()+timedelta(days=7),'total_marks':10,'results_released':False,'attempts_allowed':10})
question,_=Question.objects.update_or_create(assignment=assignment,title='Read the output',defaults={'prompt':'Write the output of print(2 + 2).','type':'output_prediction','correct_answer':['4'],'marks':10})
AssignmentAccess.objects.get_or_create(assignment=assignment,student=student)
draft,_=Assignment.objects.get_or_create(trainer=trainer,course=course,title='UI audit: draft',defaults={'total_marks':10})
Question.objects.get_or_create(assignment=draft,title='Draft question',defaults={'prompt':'Write the output of print(2 + 2).','type':'output_prediction','correct_answer':['4'],'marks':10})
completed,_=Assignment.objects.get_or_create(trainer=trainer,course=course,title='UI audit: released result',defaults={'status':'closed','total_marks':10,'results_released':True})
q,_=Question.objects.get_or_create(assignment=completed,title='Expected output comparison',defaults={'prompt':'Write the output of print(2 + 2).','type':'output_prediction','correct_answer':['4'],'marks':10})
AssignmentAccess.objects.get_or_create(assignment=completed,student=student)
submission,_=Submission.objects.get_or_create(assignment=completed,student=student,attempt=1,defaults={'expires_at':timezone.now(),'submitted_at':timezone.now(),'status':'evaluated','score':0,'percentage':0})
QuestionResponse.objects.get_or_create(submission=submission,question=q,defaults={'answer':'3','score':0,'status':'evaluated','execution':{'passed':0,'total':1,'samples':[{'accepted':False,'status':'Wrong Answer','expected_output':'4','stdout':'3','stderr':''}]}})
report,_=PerformanceReport.objects.get_or_create(trainer=trainer,student=student,evidence={'ui_test_fixture':True},defaults={'published_at':timezone.now(),'metrics':{'average_score':75,'completion_percentage':80,'coding_accuracy':50},'narrative':{'overall_performance':'UI test report: review the latest learning outcomes.','strengths':['Clear reasoning'],'weaknesses':['Check the exact output'],'coding_analysis':'Compare each output carefully.','progress_analysis':'Review the feedback before your next attempt.','recommendations':[],'trainer_feedback':'A fixture for layout verification only.'}})
(root/'.task-temp/ui-details.json').write_text(json.dumps({'assignment':assignment.pk,'draft':draft.pk,'submission':submission.pk,'report':report.pk,'student':student.pk}))
print('Detail-page fixtures prepared in the isolated browser database.')
