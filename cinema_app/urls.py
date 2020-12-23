from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter

from cinema_app.API import resources
from cinema_app.views import ProductList, Login, Logout, Registration, CreateHallView, CreateSessionView, \
    ScheduleTodayView, ScheduleTomorrowView, AvailableToEditHallView, EditHallView, PurchasedTicketsListView, \
    OrderTicketView, AdminToolsView

router = DefaultRouter()
router.register(r'users', resources.UserViewSet)
router.register(r'halls', resources.HallViewSet)
router.register(r'films', resources.FilmViewSet)
router.register(r'sessions', resources.SessionViewSet)
router.register(r'tickets', resources.TicketViewSet)

urlpatterns = [
    path('', ProductList.as_view(), name='products'),
    path('login/', Login.as_view(), name='login'),
    path('logout/', Logout.as_view(), name='logout'),
    path('registration/', Registration.as_view(), name='registration'),
    path('admin_tools/', AdminToolsView.as_view(), name='admin_tools'),
    path('admin_tools/create_hall/', CreateHallView.as_view(), name='create_hall'),
    path('admin_tools/create_session/', CreateSessionView.as_view(), name='create_session'),
    path('admin_tools/halls_list/', AvailableToEditHallView.as_view(), name='hall_list'),
    path('admin_tools/halls_list/edit/<int:pk>/', EditHallView.as_view(), name='edit_hall'),
    path('schedule_today/', ScheduleTodayView.as_view(), name='schedule_today'),
    path('schedule_tomorrow/', ScheduleTomorrowView.as_view(), name='schedule_tomorrow'),
    path('order_ticket/', OrderTicketView.as_view(), name='order_ticket'),
    path('order_history/', PurchasedTicketsListView.as_view(), name='order_history'),
    path('', include(router.urls)),
    path('api-token-auth/', views.obtain_auth_token)
]
