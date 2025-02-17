from datetime import datetime
from ...models import Payment, MaintenanceRequest, Unit

def get_admin_statistics():
    """Calculate statistics for admin dashboard"""
    stats = {
        'monthly_revenue': 0,
        'payments_paid': 0,
        'payments_pending': 0,
        'payments_overdue': 0,
        'payment_months': [],
        'payment_values': [],
        'occupancy_months': [],
        'occupancy_data': []
    }
    
    try:
        # Your existing statistics calculations...
        today = datetime.utcnow()
        start_of_month = datetime(today.year, today.month, 1)
        
        # Monthly revenue
        monthly_payments = Payment.query.filter(
            Payment.payment_date >= start_of_month,
            Payment.status == 'paid'
        ).all()
        stats['monthly_revenue'] = sum(payment.amount for payment in monthly_payments)
        
        # Payment counts
        stats['payments_paid'] = Payment.query.filter_by(status='paid').count()
        stats['payments_pending'] = Payment.query.filter_by(status='pending').count()
        stats['payments_overdue'] = Payment.query.filter_by(status='overdue').count()
        
        # Add other statistics calculations...
        
    except Exception as e:
        print(f"Error calculating statistics: {str(e)}")
        
    return stats 