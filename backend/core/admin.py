from django.contrib import admin

from .models import AuditLog, Flight, Gate, GateAssignment, ServiceRequest, User

admin.site.register(User)
admin.site.register(Gate)
admin.site.register(Flight)
admin.site.register(GateAssignment)
admin.site.register(ServiceRequest)
admin.site.register(AuditLog)
