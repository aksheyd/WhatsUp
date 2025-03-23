from django.contrib import admin

from .models import State, County, Choice, Question

# class ChoiceInline(admin.TabularInline): 
#     model = Choice
#     extra = 3

# class QuestionAdmin(admin.ModelAdmin):
#     fieldsets = [
#         (None, {"fields": ["question_text"]}),
#         ("Date information", {"fields": ["pub_date"], "classes": ["collapse"]}),
#     ]
#     inlines = [ChoiceInline]

#     list_display = ["question_text", "pub_date", "was_published_recently"]
#     list_filter = ["pub_date"]
#     search_fields = ["question_text"]

class CountyAdmin(admin.ModelAdmin):
    autocomplete_fields = ['state']


class StateAdmin(admin.ModelAdmin):
    search_fields = ['name']


admin.site.register(State, StateAdmin)
admin.site.register(County, CountyAdmin)
admin.site.register(Question)
admin.site.register(Choice)