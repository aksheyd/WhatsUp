from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
import json
import random

from .models import State, County, Choice, Question, Ordinance
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI

def TitleView(request):
    return render(request, "polls/title.html")

class StateListView(generic.ListView):
    model = State
    template_name = "polls/state_list.html"
    context_object_name = "state_list"


class CountyListView(generic.ListView):
    model = County
    template_name = "polls/county_list.html"
    context_object_name = "county_list"

    def get_queryset(self):
        # Filter counties by the state ID passed in the URL
        return County.objects.filter(state_id=self.kwargs["state_id"])


class CountyDetailView(generic.DetailView):
    model = County
    template_name = "polls/county_detail.html"
    context_object_name = "county"


class QuestionView(generic.ListView):
    template_name = "polls/question.html"
    context_object_name = "latest_question_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['state_id'] = self.kwargs['state_id']
        context['pk'] = self.kwargs['pk']
        return context
    
    def get_queryset(self):
        """
        Return the last five published questions (not including those set to be
        published in the future).
        """
        return Question.objects.filter(county_id=self.kwargs["pk"]).order_by("-pub_date")[
            :20
        ]


class DetailView(generic.DetailView):
    model = Question
    template_name = "polls/detail.html"
    pk_url_kwarg = 'pk2'  # Use pk2 from URL

    def get_queryset(self):
        """
        Filter questions by county ID and ensure they're published
        """
        return Question.objects.filter(
            county_id=self.kwargs['pk'],
            pub_date__lte=timezone.now()
        )


class ResultsView(generic.DetailView):
    model = Question
    template_name = "polls/results.html"
    pk_url_kwarg = 'pk2'  # Use pk2 from URL

    def get_queryset(self):
        """
        Filter questions by county ID and ensure they're published
        """
        return Question.objects.filter(
            county_id=self.kwargs['pk'],
            pub_date__lte=timezone.now()
        )


def vote(request, state_id, pk, pk2):
    question = get_object_or_404(Question, pk=pk2)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(
            request,
            "polls/detail.html",

            {
                'state_id': state_id,
                'pk': pk,
                'pk2': pk2,
                "question": question,
                "error_message": "You didn't select a choice.",
            },
        )
    else:
        selected_choice.votes = F("votes") + 1
        selected_choice.save()

        # Use kwargs to ensure all parameters are passed correctly
        return HttpResponseRedirect(
            reverse("polls:results", 
                   kwargs={
                       'state_id': state_id,
                       'pk': pk,
                       'pk2': pk2
                   })
        )

def generate_question(request, state_id, pk):
    county = get_object_or_404(County, pk=pk)
    
    ordinances = Ordinance.objects.filter(county=county)
    if not ordinances.exists():
        return HttpResponse("No ordinances found for this county. Working on adding counties that aren't municode.")
    
    random_ordinance = ordinances.order_by('?').first()
    if random_ordinance.text.strip() == "":
        return HttpResponse("Error: Ordinance found has no text. Please try again.")

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature="0.0")
    
    prompt = f"""Based on this ordinance, create an interesting question with 2-4 choices and indicate which choice is correct. The question should be readable for any regular citizen with not a lot of political knowledge, but still be fun in showcasing things about local laws. 
    Ordinance text: {random_ordinance.text[:2000]}
    Format the output strictly as JSON like this:
    {{"question": "Your question here", "choices": ["Choice 1", "Choice 2", "Choice 3", "Choice 4"], "correct_answer": "The exact text of the correct choice"}}
    """
    
    try:
        output = llm.invoke(prompt)
        
        output = output.content.strip()  # Remove leading/trailing whitespace
        if output.startswith("```") and output.endswith("```"):
            output = output.split("\n", 1)[1].rsplit("\n", 1)[0]  # Remove the first and last lines

        response_data = json.loads(output)
        
        # Create the question with right answer and ordinance reference
        question = Question.objects.create(
            county=county,
            question_text=response_data["question"],
            pub_date=timezone.now(),
            right_answer=response_data["correct_answer"],
            ordinance=random_ordinance
        )
        
        # Create the choices
        for choice_text in response_data["choices"]:
            Choice.objects.create(
                question=question,
                choice_text=choice_text
            )
        
        return HttpResponseRedirect(
            reverse("polls:question", 
                   kwargs={
                       'state_id': state_id,
                       'pk': pk
                   })
        )
        
    except (json.JSONDecodeError, KeyError, Exception) as e:
        return HttpResponse(f"Error generating question: {str(e)}")


