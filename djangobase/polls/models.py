import datetime

from django.db import models
from django.utils import timezone
from django.contrib import admin

# Create your models here.
class State(models.Model):
    code = models.CharField(max_length=2)
    name = models.CharField(max_length=200)
    link = models.CharField(max_length=300)

    def __str__(self):
        return self.name

class County(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    link = models.CharField(max_length=300)

    def __str__(self):
        return self.name

class Ordinance(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    url = models.URLField(max_length=500, unique=True)
    text = models.TextField()

    def __str__(self):
        return f"Ordinance for {self.county.name}"

class Question(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")
    right_answer = models.CharField(max_length=200, null=True, blank=True)
    ordinance = models.ForeignKey(Ordinance, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.question_text

    @admin.display(
        boolean=True,
        ordering="pub_date",
        description="Published recently?",
    )

    def was_published_recently(self):
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now
        
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text

