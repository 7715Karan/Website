import requests
from .utils import get_nse_option_chain_with_greeks
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from nsepython import nse_get_top_gainers, nse_get_top_losers,nse_marketStatus,nse_largedeals,nse_blockdeal,nse_fiidii,nse_events

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome {username}!")
            return redirect('option_chain:home')  # Redirect to home page
        else:
            messages.error(request, "Invalid credentials")
            return render(request, 'option_chain/login.html')

    return render(request, 'option_chain/login.html')


def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('option_chain:login')


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("option_chain:register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("option_chain:register")

        User.objects.create_user(username=username, password=password)
        messages.success(request, "Account created successfully! Please log in.")
        return redirect("option_chain:login")

    return render(request, "option_chain/register.html")

@login_required(login_url='login/')

def home(request):
    try:
        gainers_df = nse_get_top_gainers()
        losers_df = nse_get_top_losers()
        market_status = nse_marketStatus()
        block_deals_raw = nse_blockdeal()
        nse_fiidii_raw = nse_fiidii()
        nse_events_raw = nse_events()

        top_gainers = gainers_df.to_dict(orient="records")
        top_losers = losers_df.to_dict(orient="records")
        nse_event = nse_events_raw.to_dict(orient="records")
        
        nse_fiidii_data = nse_fiidii_raw.to_dict(orient="records")


        block_deals = [
            {
                "symbol": deal.get("symbol"),
                "price": deal.get("lastPrice") or deal.get("watp"),
                "qty": deal.get("totalTradedVolume") or deal.get("qty"),
                "value": deal.get("totalTradedValue") or round(deal.get("lastPrice", 0) * deal.get("qty", 0), 2)
            }
            for deal in block_deals_raw.get("data", [])
        ]

    except Exception as e:
        print("❌ Error fetching data:", e)
        import traceback
        traceback.print_exc()  # This will help debug
        top_gainers, top_losers, market_status = [], [], {}
        block_deals, nse_fiidii_data = [], []

    return render(request, "option_chain/home.html", {
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "market_status": market_status,
        "block_deals": block_deals,
        "nse_fiidii_data": nse_fiidii_data,
        "nse_event": nse_event[0:10]
    })


def option_chain_dashboard(request):

    return render(request, 'option_chain/option_chain.html')

def option_chain_view(request, symbol="NIFTY"):

    data = get_nse_option_chain_with_greeks(symbol)
    return JsonResponse(data, safe=False, json_dumps_params={"indent": 2})

@csrf_exempt
def option_chain_api(request, symbol="NIFTY"):

    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            risk_free_rate = body.get('risk_free_rate', 0.06)
            use_market_iv = body.get('use_market_iv', True)
            
            data = get_nse_option_chain_with_greeks(
                symbol=symbol, 
                risk_free_rate=risk_free_rate, 
                use_market_iv=use_market_iv
            )
        except json.JSONDecodeError:
            data = get_nse_option_chain_with_greeks(symbol)
    else:
        data = get_nse_option_chain_with_greeks(symbol)
    
    return JsonResponse(data, safe=False, json_dumps_params={"indent": 2})