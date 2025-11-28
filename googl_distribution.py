#!/usr/bin/env python3
"""
Create a smooth, integrable probability distribution curve for GOOGL based on Polymarket data.
Uses parameterized interpolation to handle wide price bins and estimate P(stock up).

Data source: "What will Google (GOOGL) hit before 2026?" market
Time horizon: ~33 days (Nov 28 to Dec 31, 2025)
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize, curve_fit
from scipy.interpolate import PchipInterpolator

# Current price and time horizon
CURRENT_PRICE = 320.28
DAYS_TO_EXPIRY = 33  # Nov 28 to Dec 31

# Polymarket data from "What will GOOGL hit before 2026?"
# These are TOUCH probabilities (will price touch X at any point before 2026)

# Upside touch probabilities: P(max price >= X)
upside_touch = {
    320: 1.000,   # Already hit
    335: 0.710,   # 71.0%
    345: 0.475,   # 47.5%
    355: 0.295,   # 29.5%
    375: 0.125,   # 12.5%
}

# Downside touch probabilities: P(min price <= X)
downside_touch = {
    305: 1.000,   # Already hit
    290: 0.345,   # 34.5%
    285: 0.235,   # 23.5%
    275: 0.140,   # 14.0%
    260: 0.055,   # 5.5%
    250: 0.035,   # 3.5%
    230: 0.017,   # 1.7%
    200: 0.018,   # 1.8%
}

print("="*70)
print("GOOGL PROBABILITY DISTRIBUTION ANALYSIS")
print("="*70)
print(f"Current Price: ${CURRENT_PRICE}")
print(f"Time Horizon: {DAYS_TO_EXPIRY} days (until Dec 31, 2025)")
print()

# ============================================================================
# METHOD 1: Convert touch probabilities to terminal distribution
# For a random walk, P(touch X) relates to terminal distribution via reflection
# P(max >= X | S0) ≈ 2 * P(S_T >= X) for X > S0 (simplified)
# ============================================================================

print("Converting touch probabilities to terminal distribution...")

# Build CDF points from touch probabilities
# For upside: P(touch X) ≈ 2 * (1 - CDF(X)) for barrier above current price
# For downside: P(touch X) ≈ 2 * CDF(X) for barrier below current price

cdf_points = []

# Downside: P(touch X) ≈ 2 * CDF(X), so CDF(X) ≈ P(touch)/2
for price, touch_prob in downside_touch.items():
    if price < CURRENT_PRICE:
        # Apply reflection principle adjustment
        implied_cdf = touch_prob / 2  # First approximation
        cdf_points.append((price, implied_cdf))

# Upside: P(touch X) ≈ 2 * (1 - CDF(X)), so CDF(X) ≈ 1 - P(touch)/2
for price, touch_prob in upside_touch.items():
    if price > CURRENT_PRICE:
        implied_cdf = 1 - touch_prob / 2
        cdf_points.append((price, implied_cdf))

# Add current price as ~50th percentile anchor
cdf_points.append((CURRENT_PRICE, 0.50))

# Sort by price
cdf_points.sort(key=lambda x: x[0])
print(f"CDF anchor points: {len(cdf_points)}")
for p, c in cdf_points:
    print(f"  ${p}: CDF = {c:.3f}")

# ============================================================================
# METHOD 2: Fit a parametric model (Mixture of Gaussians or Skew-Normal)
# ============================================================================

def mixture_gaussian_cdf(x, mu1, sigma1, mu2, sigma2, w1):
    """Mixture of 2 Gaussians CDF."""
    w2 = 1 - w1
    return w1 * norm.cdf(x, mu1, sigma1) + w2 * norm.cdf(x, mu2, sigma2)

def mixture_gaussian_pdf(x, mu1, sigma1, mu2, sigma2, w1):
    """Mixture of 2 Gaussians PDF."""
    w2 = 1 - w1
    return w1 * norm.pdf(x, mu1, sigma1) + w2 * norm.pdf(x, mu2, sigma2)

def objective(params):
    """Fit mixture to CDF constraints."""
    mu1, sigma1, mu2, sigma2, w1 = params
    
    if sigma1 <= 0 or sigma2 <= 0 or w1 < 0 or w1 > 1:
        return 1e10
    
    error = 0
    for price, target_cdf in cdf_points:
        pred_cdf = mixture_gaussian_cdf(price, mu1, sigma1, mu2, sigma2, w1)
        error += (pred_cdf - target_cdf) ** 2
    
    return error

# Initial guess based on current price and typical volatility
initial_params = [CURRENT_PRICE, 15, CURRENT_PRICE + 5, 25, 0.7]

bounds = [
    (300, 340),   # mu1
    (5, 40),      # sigma1
    (300, 360),   # mu2
    (10, 50),     # sigma2
    (0.2, 0.9),   # weight1
]

print("\nFitting Gaussian Mixture Model...")
result = minimize(objective, initial_params, bounds=bounds, method='L-BFGS-B')
params_gmm = result.x

print(f"  Gaussian 1: μ=${params_gmm[0]:.2f}, σ=${params_gmm[1]:.2f}, weight={params_gmm[4]:.2f}")
print(f"  Gaussian 2: μ=${params_gmm[2]:.2f}, σ=${params_gmm[3]:.2f}, weight={1-params_gmm[4]:.2f}")
print(f"  Fit error: {result.fun:.6f}")

# ============================================================================
# Calculate key probabilities
# ============================================================================

prices = np.linspace(200, 450, 2000)
pdf_values = mixture_gaussian_pdf(prices, *params_gmm)
cdf_values = mixture_gaussian_cdf(prices, *params_gmm)

# Verify integral
integral = np.trapz(pdf_values, prices)
print(f"\nPDF integral (should be ~1.0): {integral:.6f}")

# Probability stock is UP (> current price)
prob_up = 1 - mixture_gaussian_cdf(CURRENT_PRICE, *params_gmm)
prob_down = mixture_gaussian_cdf(CURRENT_PRICE, *params_gmm)

print(f"\n{'='*70}")
print("KEY PROBABILITY ESTIMATES")
print('='*70)
print(f"\n*** P(GOOGL > ${CURRENT_PRICE} by Dec 31) = {prob_up*100:.1f}% ***")
print(f"*** P(GOOGL < ${CURRENT_PRICE} by Dec 31) = {prob_down*100:.1f}% ***")

# Expected value and stats
expected_value = np.trapz(prices * pdf_values, prices)
variance = np.trapz((prices - expected_value)**2 * pdf_values, prices)
std_dev = np.sqrt(variance)

print(f"\nExpected Price: ${expected_value:.2f}")
print(f"Standard Deviation: ${std_dev:.2f}")
print(f"Expected Return: {(expected_value/CURRENT_PRICE - 1)*100:+.2f}%")

# Percentiles
print(f"\nPercentiles:")
for p in [5, 10, 25, 50, 75, 90, 95]:
    idx = np.argmin(np.abs(cdf_values - p/100))
    print(f"  {p}th: ${prices[idx]:.2f}")

# Compare model vs market
print(f"\nModel vs Market Touch Probabilities:")
print(f"{'Price':<10} {'Market':<12} {'Model':<12} {'Diff':<10}")
print("-" * 44)

for price, market_prob in sorted(upside_touch.items()):
    if price > CURRENT_PRICE:
        model_touch = 2 * (1 - mixture_gaussian_cdf(price, *params_gmm))
        model_touch = min(model_touch, 1.0)
        diff = model_touch - market_prob
        print(f"${price:<9} {market_prob*100:>6.1f}%      {model_touch*100:>6.1f}%      {diff*100:>+5.1f}%")

for price, market_prob in sorted(downside_touch.items(), reverse=True):
    if price < CURRENT_PRICE:
        model_touch = 2 * mixture_gaussian_cdf(price, *params_gmm)
        model_touch = min(model_touch, 1.0)
        diff = model_touch - market_prob
        print(f"${price:<9} {market_prob*100:>6.1f}%      {model_touch*100:>6.1f}%      {diff*100:>+5.1f}%")

# ============================================================================
# Create visualization
# ============================================================================

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Plot 1: PDF
ax1 = axes[0]
ax1.fill_between(prices, pdf_values, alpha=0.4, color='#3498db', label='Probability Density')
ax1.plot(prices, pdf_values, color='#2980b9', linewidth=2.5)

# Shade up/down regions
mask_up = prices > CURRENT_PRICE
mask_down = prices < CURRENT_PRICE
ax1.fill_between(prices[mask_up], pdf_values[mask_up], alpha=0.3, color='#27ae60', label=f'Upside ({prob_up*100:.1f}%)')
ax1.fill_between(prices[mask_down], pdf_values[mask_down], alpha=0.3, color='#e74c3c', label=f'Downside ({prob_down*100:.1f}%)')

ax1.axvline(x=CURRENT_PRICE, color='#e74c3c', linestyle='--', linewidth=2.5, label=f'Current ${CURRENT_PRICE}')
ax1.axvline(x=expected_value, color='#9b59b6', linestyle=':', linewidth=2, label=f'Expected ${expected_value:.0f}')

ax1.set_xlabel('GOOGL Price ($)', fontsize=12)
ax1.set_ylabel('Probability Density', fontsize=12)
ax1.set_title('Terminal Price Distribution (Dec 31, 2025)', fontsize=13, fontweight='bold')
ax1.set_xlim(270, 400)
ax1.legend(loc='upper right', fontsize=9)
ax1.grid(alpha=0.3)

# Add probability annotation
ax1.text(0.03, 0.95, f'P(Up) = {prob_up*100:.1f}%', transform=ax1.transAxes, 
         fontsize=14, fontweight='bold', color='#27ae60',
         bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

# Plot 2: CDF with market data points
ax2 = axes[1]
ax2.plot(prices, cdf_values, color='#2980b9', linewidth=2.5, label='Fitted CDF')

# Plot market-implied CDF points
cdf_prices = [p for p, c in cdf_points]
cdf_vals = [c for p, c in cdf_points]
ax2.scatter(cdf_prices, cdf_vals, s=80, color='#e74c3c', zorder=5, label='Market-Implied Points')

ax2.axvline(x=CURRENT_PRICE, color='#e74c3c', linestyle='--', linewidth=2)
ax2.axhline(y=0.5, color='gray', linestyle=':', alpha=0.5)

ax2.set_xlabel('GOOGL Price ($)', fontsize=12)
ax2.set_ylabel('Cumulative Probability', fontsize=12)
ax2.set_title('Cumulative Distribution Function', fontsize=13, fontweight='bold')
ax2.set_xlim(250, 400)
ax2.set_ylim(0, 1)
ax2.legend(loc='lower right', fontsize=10)
ax2.grid(alpha=0.3)

# Add annotation for P(up)
ax2.fill_between([CURRENT_PRICE, 400], [1-prob_up, 1-prob_up], [1, 1], alpha=0.2, color='#27ae60')
ax2.text(CURRENT_PRICE + 5, 1 - prob_up/2, f'P(Up) = {prob_up*100:.1f}%', 
         fontsize=11, color='#27ae60', fontweight='bold')

plt.suptitle('GOOGL Price Probability Analysis (Polymarket Data)\n"What will GOOGL hit before 2026?"', 
             fontsize=14, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig('googl_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nSaved to: googl_distribution.png")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"""
Based on Polymarket's "What will GOOGL hit before 2026?" market:

Current Price: ${CURRENT_PRICE}
Time Horizon: {DAYS_TO_EXPIRY} days

ANSWER: The probability that GOOGL is HIGHER than ${CURRENT_PRICE} 
        by December 31, 2025 is approximately {prob_up*100:.1f}%

Key insights:
- Expected price: ${expected_value:.2f} ({(expected_value/CURRENT_PRICE-1)*100:+.1f}% from current)
- 71% chance of touching $335 at some point
- 47.5% chance of touching $345 at some point  
- 34.5% chance of dipping to $290 at some point

Note: Touch probabilities are converted to terminal distribution using
the reflection principle approximation for barrier options.
""")
