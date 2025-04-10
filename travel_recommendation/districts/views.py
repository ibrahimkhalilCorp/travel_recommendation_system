from django.views.generic import View
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import District
from .serializers import TopDistrictSerializer, TravelRecommendationSerializer
from .services import (
    fetch_districts_data,
    get_district_metrics,
    run_async_fetch_travel
)
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)


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


class TopDistrictsView(APIView):
    def get(self, request):
        start_time = time.time()

        # Fetch precomputed or cached metrics
        district_data = get_district_metrics()

        if not district_data:
            return Response({"error": "No data available"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Sort by temperature and PM2.5, take top 10
        district_data.sort(key=lambda x: (x['avg_temperature'], x['avg_pm25']))
        top_districts = district_data[:10]
        serializer = TopDistrictSerializer(top_districts, many=True)

        elapsed_time = (time.time() - start_time) * 1000
        logger.info(f"Top districts processed in {elapsed_time:.2f} ms")
        if elapsed_time > 500:
            logger.warning(f"Response time exceeded 500 ms: {elapsed_time:.2f} ms")

        return Response(serializer.data, status=status.HTTP_200_OK)


class TravelRecommendationView(View):
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

    def post(self, request):
        start_time = time.time()
        districts = District.objects.all().order_by('name')
        context = {
            'districts': districts,
            'today': datetime.now(),
            'seven_days_later': datetime.now() + timedelta(days=7)
        }

        try:
            current_district_name = request.POST.get('current_district')
            destination_district_name = request.POST.get('destination_district')
            travel_date_str = request.POST.get('travel_date')

            if not all([current_district_name, destination_district_name, travel_date_str]):
                raise ValueError("All fields (current district, destination district, travel date) are required")

            current_district = District.objects.get(name=current_district_name)
            destination_district = District.objects.get(name=destination_district_name)
            travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            if travel_date < today or travel_date > (today + timedelta(days=7)):
                raise ValueError("Travel date must be within the next 7 days from today")

            # Fetch weather and air quality data asynchronously
            current_district_data = {'latitude': current_district.latitude, 'longitude': current_district.longitude}
            destination_district_data = {'latitude': destination_district.latitude,
                                         'longitude': destination_district.longitude}
            current_data, dest_data = run_async_fetch_travel(current_district_data, destination_district_data,
                                                             travel_date)

            current_temp = current_data['temp']
            current_pm25 = current_data['pm25']
            dest_temp = dest_data['temp']
            dest_pm25 = dest_data['pm25']

            # Generate recommendation
            temp_diff = current_temp - dest_temp
            pm25_diff = current_pm25 - dest_pm25
            if temp_diff > 0 and pm25_diff > 0:
                recommendation = "Recommended"
                reason = f"Your destination is {temp_diff:.1f}°C cooler and has {pm25_diff:.1f} µg/m³ better air quality. Enjoy your trip!"
            else:
                recommendation = "Not Recommended"
                reasons = []
                if temp_diff <= 0:
                    reasons.append(f"hotter by {abs(temp_diff):.1f}°C" if temp_diff < 0 else "same temperature")
                if pm25_diff <= 0:
                    reasons.append(
                        f"worse air quality by {abs(pm25_diff):.1f} µg/m³" if pm25_diff < 0 else "same air quality")
                reason = f"Your destination is {' and '.join(reasons)} than your current district. It’s better to stay where you are."

            response_data = {
                'recommendation': recommendation,
                'reason': reason,
                'current': {'temp': current_temp, 'pm25': current_pm25},
                'destination': {'temp': dest_temp, 'pm25': dest_pm25}
            }

            elapsed_time = (time.time() - start_time) * 1000
            logger.info(f"Travel recommendation processed in {elapsed_time:.2f} ms")
            if elapsed_time > 500:
                logger.warning(f"Response time exceeded 500 ms: {elapsed_time:.2f} ms")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context['recommendation'] = response_data
                return render(request, 'index.html', context)
            return Response(response_data, status=status.HTTP_200_OK)

        except District.DoesNotExist:
            error_msg = "One or both selected districts are invalid"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context['error'] = error_msg
                return render(request, 'index.html', context)
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context['error'] = error_msg
                return render(request, 'index.html', context)
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in travel recommendation: {str(e)}")
            error_msg = "An unexpected error occurred"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                context['error'] = error_msg
                return render(request, 'index.html', context)
            return Response({"error": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)