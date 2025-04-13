from django import template

register = template.Library()

@register.filter
def has_makeup(attendance_dict, date_str):
    for student_id, records in attendance_dict.items():
        if date_str in records and records[date_str].get('is_makeup', False):
            return True
    return False