from django.contrib import admin
from .models import JobPosting, JobApplication, JobExperience, Note


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'company_name', 'location', 'remote_ok', 'scraped_at', 'added_by')
    list_filter = ('remote_ok', 'scraped_at', 'scraping_success')
    search_fields = ('job_title', 'company_name', 'location')
    readonly_fields = ('job_posting_id', 'scraped_at', 'updated_at')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job_posting', 'user', 'status', 'applied_date', 'created_at')
    list_filter = ('status', 'applied_date', 'created_at')
    search_fields = ('job_posting__job_title', 'job_posting__company_name', 'user__username')
    readonly_fields = ('job_application_id', 'created_at', 'updated_at')


@admin.register(JobExperience)
class JobExperienceAdmin(admin.ModelAdmin):
    list_display = ('job_posting', 'experience', 'user', 'relevance', 'match_score', 'created_date')
    list_filter = ('relevance', 'creation_source', 'created_date')
    search_fields = ('job_posting__job_title', 'experience__title', 'user__username')
    readonly_fields = ('job_experience_id', 'created_date')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'job', 'user', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at', 'updated_at')
    search_fields = ('title', 'body', 'job__job_title', 'job__company_name', 'user__username')
    readonly_fields = ('note_id', 'created_at', 'updated_at')
    raw_id_fields = ('job', 'user')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('job', 'user')