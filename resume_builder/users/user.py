# userapp/views.py

from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
# from django.utils import timezone
import json

from datetime import datetime, timezone
import uuid
import json

# from . import get_postgres_connection
# from entrov.mongodb.auth import authenticate
# import psycopg2
# from psycopg2.extras import RealDictCursor
# Connect to MongoDB
# user_collection = users_db['users']

# userapp/views.py

from django.shortcuts import render

# Use the custom user model if you extended it
User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
class UserCreateView(View):
    def post(self, request):

        try:
            # Parse JSON or form-encoded data
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            # Get user details from the request data
            email = data.get('email')
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            google_id = data.get('google_id')

            # Use get_or_create to find an existing user or create a new one
            user, created = User.objects.get_or_create(
                email=email, google_id=google_id,
                defaults={
                    'user_id': uuid.uuid4(),
                    'email': email,  # Set username as email (can be modified as needed)
                    'first_name': first_name,
                    'last_name': last_name,
                    'google_id': google_id,
                    'last_login': datetime.now(timezone.utc),
                    'login_count': 1,
                    'terms_and_conditions_accepted': False  # Default to False initially
                }
            )

            if not created:
                # If the user exists, update the last login timestamp
                user.last_login = datetime.now(timezone.utc)
                user.login_count = user.login_count + 1
                user.save(update_fields=['last_login', 'login_count'])

            # Respond with a JSON object indicating if the user already exists or was created
            return JsonResponse({"exists": not created, "user_id": str(user.user_id)}, status=200 if created else 201)

        except json.JSONDecodeError:
            # Handle case where JSON decoding fails
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            # Catch other exceptions and return the error message
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class TermsConditionsView(View):
    def post(self, request):
        # Authenticate using the Authorization token from the headers
        # authenticated = authenticate(request.META.get('HTTP_AUTHORIZATION'))
        # if not authenticated:
        #     return JsonResponse({'error': 'Authorization failed'}, status=400)

        try:
            # Parse JSON or form-encoded data
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            user_id = data.get('user_id')

            # Retrieve user by ID using ORM filter
            user = User.objects.filter(user_id=user_id).first()
            if not user:
                # Return 404 if user is not found
                return JsonResponse({"error": "User not found"}, status=404)

            # Update the terms and conditions acceptance flag
            user.terms_and_conditions_accepted = True
            user.save(update_fields=['terms_and_conditions_accepted'])

            # Return success response
            return JsonResponse({"success": True, "message": "Terms and conditions accepted"}, status=200)

        except json.JSONDecodeError:
            # Handle JSON decode error
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            # Catch other exceptions and return the error message
            return JsonResponse({"error": str(e)}, status=500)