# apps/core/admin.py
from django.contrib import admin
from .models import Workspace, WorkspaceMember, Client, Service, Appointment, Consultation

admin.site.register(Workspace)
admin.site.register(WorkspaceMember)
admin.site.register(Client)
admin.site.register(Service)
admin.site.register(Appointment)
admin.site.register(Consultation)
