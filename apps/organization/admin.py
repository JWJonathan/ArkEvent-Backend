from django.contrib import admin
from .models import Organization, OrganizationMember

class OrganizationMemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 1

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'type', 'city', 'country', 'verified', 'created_at')
    list_filter = ('type', 'verified', 'country')
    search_fields = ('name', 'slug', 'email', 'phone', 'city')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [OrganizationMemberInline]
    ordering = ('-created_at',)

@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ('organization', 'user', 'org_role', 'joined_at')
    list_filter = ('org_role', 'joined_at')
    search_fields = ('organization__name', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'joined_at', 'created_at', 'updated_at')
