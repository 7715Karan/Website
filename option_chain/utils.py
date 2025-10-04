import numpy as np
from scipy.stats import norm
from datetime import datetime
import math
from nsepython import nse_optionchain_scrapper



def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):

    if T <= 0 or sigma <= 0:
        return {
            'price': 0,
            'delta': 0,
            'gamma': 0,
            'theta': 0,
            'vega': 0,
            'rho': 0
        }
    
    # Calculate d1 and d2
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    # Standard normal CDF and PDF
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    n_d1 = norm.pdf(d1)
    
    if option_type == 'call':
        price = S*N_d1 - K*np.exp(-r*T)*N_d2
        delta = N_d1
        rho = K*T*np.exp(-r*T)*N_d2 / 100  # Divided by 100 for percentage point change
        
    else:  
        price = K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)
        delta = N_d1 - 1
        rho = -K*T*np.exp(-r*T)*norm.cdf(-d2) / 100  # Divided by 100 for percentage point change
    
    gamma = n_d1 / (S*sigma*np.sqrt(T))
    theta = (-S*n_d1*sigma/(2*np.sqrt(T)) - r*K*np.exp(-r*T)*N_d2) / 365  # Per day
    if option_type == 'put':
        theta = (-S*n_d1*sigma/(2*np.sqrt(T)) + r*K*np.exp(-r*T)*norm.cdf(-d2)) / 365  # Per day
    
    vega = S*n_d1*np.sqrt(T) / 100 
    
    return {
        'price': max(price, 0),
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'rho': rho
    }

def calculate_implied_volatility(market_price, S, K, T, r, option_type='call', max_iterations=100, tolerance=1e-6):

    if T <= 0:
        return 0
    
    # Initial guess for volatility
    sigma = 0.2
    
    for i in range(max_iterations):
        bs_result = black_scholes_greeks(S, K, T, r, sigma, option_type)
        
        price_diff = bs_result['price'] - market_price
        vega = bs_result['vega'] * 100  
        
        if abs(price_diff) < tolerance or vega == 0:
            break
            
        sigma = sigma - price_diff / vega
        sigma = max(sigma, 0.001)  
        
    return sigma

def get_nse_option_chain_with_greeks(symbol="NIFTY", risk_free_rate=0.06, use_market_iv=True):

    try:
        symbol = symbol.upper()
        if symbol == "NIFTY":
            symbol = "NIFTY"

        option_data = nse_optionchain_scrapper(symbol)

        if not option_data or 'records' not in option_data or 'data' not in option_data['records']:
            raise ValueError(f"No option chain data found for {symbol}")

        records = option_data['records']['data']
        expiry_dates = option_data['records'].get('expiryDates', [])

        if not expiry_dates:
            raise ValueError(f"No expiry dates found for {symbol}")

        underlying_value = option_data['records'].get('underlyingValue', 0)
        if underlying_value == 0:
            strike_prices = [record.get('strikePrice', 0) for record in records]
            underlying_value = np.median(strike_prices) if strike_prices else 0

        expiry_dates_dt = [datetime.strptime(date, '%d-%b-%Y') for date in expiry_dates]
        latest_expiry = min(expiry_dates_dt).strftime('%d-%b-%Y')
        
        expiry_dt = datetime.strptime(latest_expiry, '%d-%b-%Y')
        current_dt = datetime.now()
        days_to_expiry = (expiry_dt - current_dt).days
        if days_to_expiry <= 0:
            days_to_expiry = 1
        time_to_expiry = days_to_expiry / 365.0

        processed_data = []
        for record in records:
            if record.get('expiryDate') == latest_expiry:
                strike_price = record.get('strikePrice', 0)
                
                # Call option data
                call_data = record.get('CE', {})
                call_ltp = call_data.get('lastPrice', 0)
                call_oi = call_data.get('openInterest', 0)
                call_change_oi = call_data.get('changeinOpenInterest', 0)
                call_volume = call_data.get('totalTradedVolume', 0)
                put_data = record.get('PE', {})
                put_ltp = put_data.get('lastPrice', 0)
                put_oi = put_data.get('openInterest', 0)
                put_change_oi = put_data.get('changeinOpenInterest', 0)
                put_volume = put_data.get('totalTradedVolume', 0)
                
                call_greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0, 'iv': 0}
                put_greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0, 'iv': 0}
                
                if underlying_value > 0 and time_to_expiry > 0:
                    
                    if call_ltp > 0:
                        if use_market_iv:
                            iv_call = calculate_implied_volatility(
                                call_ltp, underlying_value, strike_price, 
                                time_to_expiry, risk_free_rate, 'call'
                            )
                            call_greeks['iv'] = iv_call
                            
                            if iv_call > 0:
                                bs_call = black_scholes_greeks(
                                    underlying_value, strike_price, time_to_expiry,
                                    risk_free_rate, iv_call, 'call'
                                )
                                call_greeks.update({
                                    'delta': round(bs_call['delta'], 4),
                                    'gamma': round(bs_call['gamma'], 6),
                                    'theta': round(bs_call['theta'], 4),
                                    'vega': round(bs_call['vega'], 4),
                                    'rho': round(bs_call['rho'], 4)
                                })
                        else:
                            # Use assumed volatility of 20%
                            bs_call = black_scholes_greeks(
                                underlying_value, strike_price, time_to_expiry,
                                risk_free_rate, 0.2, 'call'
                            )
                            call_greeks.update({
                                'delta': round(bs_call['delta'], 4),
                                'gamma': round(bs_call['gamma'], 6),
                                'theta': round(bs_call['theta'], 4),
                                'vega': round(bs_call['vega'], 4),
                                'rho': round(bs_call['rho'], 4),
                                'iv': 0.2
                            })
                    
                    if put_ltp > 0:
                        if use_market_iv:
                            iv_put = calculate_implied_volatility(
                                put_ltp, underlying_value, strike_price,
                                time_to_expiry, risk_free_rate, 'put'
                            )
                            put_greeks['iv'] = iv_put
                            
                            if iv_put > 0:
                                bs_put = black_scholes_greeks(
                                    underlying_value, strike_price, time_to_expiry,
                                    risk_free_rate, iv_put, 'put'
                                )
                                put_greeks.update({
                                    'delta': round(bs_put['delta'], 4),
                                    'gamma': round(bs_put['gamma'], 6),
                                    'theta': round(bs_put['theta'], 4),
                                    'vega': round(bs_put['vega'], 4),
                                    'rho': round(bs_put['rho'], 4)
                                })
                        else:
                            bs_put = black_scholes_greeks(
                                underlying_value, strike_price, time_to_expiry,
                                risk_free_rate, 0.2, 'put'
                            )
                            put_greeks.update({
                                'delta': round(bs_put['delta'], 4),
                                'gamma': round(bs_put['gamma'], 6),
                                'theta': round(bs_put['theta'], 4),
                                'vega': round(bs_put['vega'], 4),
                                'rho': round(bs_put['rho'], 4),
                                'iv': 0.2
                            })

                processed_record = {
                    'strike_price': strike_price,
                    'expiry_date': latest_expiry,
                    'underlying_price': underlying_value,
                    'days_to_expiry': days_to_expiry,
                    
                    'call_oi': call_oi,
                    'call_change_oi': call_change_oi,
                    'call_ltp': call_ltp,
                    'call_volume': call_volume,
                    'call_delta': call_greeks['delta'],
                    'call_gamma': call_greeks['gamma'],
                    'call_theta': call_greeks['theta'],
                    'call_vega': call_greeks['vega'],
                    'call_rho': call_greeks['rho'],
                    'call_iv': round(call_greeks['iv'], 4),
                    
                    'put_oi': put_oi,
                    'put_change_oi': put_change_oi,
                    'put_ltp': put_ltp,
                    'put_volume': put_volume,
                    'put_delta': put_greeks['delta'],
                    'put_gamma': put_greeks['gamma'],
                    'put_theta': put_greeks['theta'],
                    'put_vega': put_greeks['vega'],
                    'put_rho': put_greeks['rho'],
                    'put_iv': round(put_greeks['iv'], 4),
                    
                    'pcr_oi': put_oi / call_oi if call_oi > 0 else 0,  # Put-Call Ratio (OI)
                    'pcr_volume': put_volume / call_volume if call_volume > 0 else 0  # Put-Call Ratio (Volume)
                }
                processed_data.append(processed_record)

        if not processed_data:
            raise ValueError(f"No option chain data found for expiry date {latest_expiry}")

        return {
            'symbol': symbol,
            'expiry_date': latest_expiry,
            'underlying_price': underlying_value,
            'days_to_expiry': days_to_expiry,
            'risk_free_rate': risk_free_rate,
            'data': processed_data
        }
        
    except Exception as e:
        return {'error': f"Failed to fetch option chain data with Greeks: {str(e)}"}

