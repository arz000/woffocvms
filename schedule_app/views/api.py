from django.http import JsonResponse
from django.db.models import Q
import json
from schedule_app.models import Role, VolunteerProfile

def search_volunteers(request):
    """Return JSON list of volunteers matching the query for Alpine.js autocomplete."""
    q = request.GET.get('q', '').strip()
    volunteers = VolunteerProfile.objects.select_related('user')
    if q:
        volunteers = volunteers.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q)
        )[:15]
    results = [
        {'id': vol.id, 'label': f"{vol.user.get_full_name()} ({vol.user.username})"}
        for vol in volunteers
    ]
    return JsonResponse({'results': results})

def api_update_role(request):
    """API Endpoint to update a role via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_id = data.get('role_id')
            name = data.get('name')
            description = data.get('description')
            capabilities = data.get('capabilities', [])
            
            if role_id:
                role = Role.objects.get(id=role_id)
                if name:
                    role.name = name
                if description is not None:
                    role.description = description
                role.save()
            else:
                if not name:
                    return JsonResponse({'error': 'Role name is required'}, status=400)
                role = Role.objects.create(
                    name=name,
                    description=description or '',
                    theme='emerald'
                )
                
            role.capabilities.set(capabilities)
            role.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)
    
def api_update_ministries(request):
    """API Endpoint to update a user's ministries via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile_id = data.get('profile_id')
            ministry_ids = data.get('ministry_ids', [])
            
            profile = VolunteerProfile.objects.get(id=profile_id)
            profile.ministries.set(ministry_ids)
            profile.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

def api_assign_role(request):
    """API Endpoint to assign a user to a role via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_id = data.get('role_id')
            user_id = data.get('user_id')
            
            role = Role.objects.get(id=role_id)
            profile = VolunteerProfile.objects.get(id=user_id)
            profile.role = role
            profile.save()
            
            return JsonResponse({
                'success': True,
                'user': {
                    'id': profile.id,
                    'name': profile.user.get_full_name() or profile.user.username,
                    'email': profile.user.email
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=405)

def api_remove_role(request):
    """API Endpoint to remove a user from a role via POST request."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            profile = VolunteerProfile.objects.get(id=user_id)
            profile.role = None
            profile.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=405)

def api_delete_record(request):
    """Global API Endpoint to securely delete any allowed model record."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            model_name = data.get('model')
            record_id = data.get('id')
            
            # Whitelist of models that can be deleted via this endpoint
            from schedule_app.models import Ministry, Event, Role
            ALLOWED_MODELS = {
                'Ministry': Ministry,
                'Event': Event,
                'Role': Role
            }
            
            model_class = ALLOWED_MODELS.get(model_name)
            if not model_class:
                return JsonResponse({'error': f'Model {model_name} is not allowed or does not exist.'}, status=400)
                
            model_class.objects.filter(id=record_id).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=405)
