from django.shortcuts import render
from .models import District
from .services import fetch_districts_data


class IndexView(View):
    def get(self, request):
        districts = District.objects.all().order_by('name')
        if not districts.exists():
            try:
                districts_data = fetch_districts_data()
                if not districts_data:
                    context = {
                        'districts': [],
                        'today': datetime.now(),
                        'seven_days_later': datetime.now() + timedelta(days=7),
                        'error': "No district data available"
                    }
                    return render(request, 'index.html', context)
                for district_data in districts_data:
                    District.objects.get_or_create(
                        name=district_data['name'],
                        latitude=district_data['latitude'],
                        longitude=district_data['longitude']
                    )
                districts = District.objects.all().order_by('name')
            except Exception as e:
                context = {
                    'districts': [],
                    'today': datetime.now(),
                    'seven_days_later': datetime.now() + timedelta(days=7),
                    'error': f"Error loading districts: {str(e)}"
                }
                return render(request, 'index.html', context)
        
        context = {
            'districts': districts,
            'today': datetime.now(),
            'seven_days_later': datetime.now() + timedelta(days=7)
        }
        return render(request, 'index.html', context)