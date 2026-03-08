import random
import math

def generate_hourly_prices(base_price=75, volatility=10):
    """
    Generates a list of 24 hourly electricity prices in $/MWh.
    
    Args:
        base_price: The average price for the day.
        volatility: How much the price fluctuates randomly.
    """
    prices = []
    
    for hour in range(24):
        # Create a double-peak pattern (morning and evening)
        # Peak 1: Hour 8 (Morning rush)
        # Peak 2: Hour 19 (Evening peak)
        sine_wave = math.sin((hour - 4) * math.pi / 12) * 15
        evening_bump = 20 if 17 <= hour <= 21 else 0
        
        # Add some random market noise
        noise = random.uniform(-volatility, volatility)
        
        # Calculate final price
        price = base_price + sine_wave + evening_bump + noise
        prices.append(round(max(5, price), 2)) # Ensure price doesn't go below $5
        
    return prices

# Example usage:
daily_prices = generate_hourly_prices()
for hr, pr in enumerate(daily_prices):
    print(f"Hour {hr:02d}: ${pr}")