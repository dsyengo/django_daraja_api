from django.urls import path
from .views import InitiateSTKPushView, MpesaCallbackView

urlpatterns = [
    path('stk-push/', InitiateSTKPushView.as_view(), name='stk-push'),
    path('callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
]