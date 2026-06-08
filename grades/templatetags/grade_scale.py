from django import template

from grades.models import Grade

register = template.Library()


@register.filter
def grade_scale_class(score):
    scale = Grade.scale_for_score(score)
    return scale['class'] if scale else ''


@register.filter
def grade_scale_label(score):
    scale = Grade.scale_for_score(score)
    return scale['label'] if scale else ''


@register.filter
def grade_scale_color(score):
    scale = Grade.scale_for_score(score)
    return scale['color'] if scale else 'var(--gray-300)'
