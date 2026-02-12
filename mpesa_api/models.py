from django.db import models

class MpesaTransaction(models.Model):
    """
    Stores M-Pesa transactions.
    
    Key Optimization:
    - checkout_request_id has db_index=True. 
    - This allows O(log n) lookup speed, which is critical since we are processing
      callbacks synchronously. We must find the record fast to avoid timeout.
    """
    
    # Safaricom's Receipt (e.g., QWE123...)
    transaction_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # The ID we use to track the request
    checkout_request_id = models.CharField(max_length=50, unique=True, db_index=True)
    
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    
    # Stores the failure reason or success message
    result_desc = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} - {self.status}"