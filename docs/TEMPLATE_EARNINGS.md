# Template Earnings and Withdrawal System

## Overview
This document describes the template earnings and withdrawal system implemented for the BotMather backend.

## Features

### 1. Template Balance Tracking
Template authors earn money when users purchase their templates. These earnings are tracked separately from the main user balance in the `template_balance` field.

### 2. Commission Distribution
When a template is sold:
- **80%** of the sale price goes to the template author's `template_balance`
- **20%** is retained as platform commission

This happens automatically when a template order's `payment_status` becomes `True` and `status` is `CONFIRM`.

### 3. Withdrawal System
Template authors can request to withdraw their earnings by providing:
- Amount to withdraw
- Card number (13-19 digits)
- Card owner name

## API Endpoints

### List Withdrawal Requests
```
GET /template/withdrawal/
Authorization: Bearer <token>
```

Returns all withdrawal requests for the authenticated user.

### Create Withdrawal Request
```
POST /template/withdrawal/
Authorization: Bearer <token>
Content-Type: application/json

{
  "amount": "500.00",
  "card_number": "8600123456789012",
  "card_owner": "John Doe"
}
```

### Get Withdrawal Details
```
GET /template/withdrawal/{id}/
Authorization: Bearer <token>
```

### Delete Pending Withdrawal
```
DELETE /template/withdrawal/{id}/
Authorization: Bearer <token>
```

Only pending withdrawals can be deleted.

### Check Balance
```
GET /accounts/balance/
Authorization: Bearer <token>
```

Returns:
```json
{
  "balance": 10000,
  "template_balance": "500.00"
}
```

## Admin Workflow

### Approving Withdrawals

1. Navigate to **Template Withdrawal Requests** in Django Admin
2. Select pending withdrawal requests
3. Choose action: **Approve selected withdrawal requests**
4. The system will:
   - Check if user has sufficient balance
   - Deduct the amount from user's `template_balance`
   - Mark the request as approved
   - Record who approved and when

### Rejecting Withdrawals

1. Navigate to **Template Withdrawal Requests** in Django Admin
2. Select pending withdrawal requests
3. Choose action: **Reject selected withdrawal requests**
4. Optionally, edit individual requests to add a rejection reason

### Manual Review

For individual requests:
1. Click on the withdrawal request
2. Change status to "Approved" or "Rejected"
3. Add rejection reason if rejecting
4. Save

The system automatically handles balance deduction for approved requests.

## Database Schema

### User Model Changes
```python
template_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
```

### Template Order Model Changes
```python
commission_paid = models.BooleanField(default=False)
```

### Template Withdrawal Request Model
```python
class TemplateWithdrawalRequestModel:
    user: ForeignKey
    amount: DecimalField
    card_number: CharField(max_length=20)
    card_owner: CharField(max_length=255)
    status: CharField  # pending, approved, rejected
    rejection_reason: TextField (optional)
    reviewed_by: ForeignKey (optional)
    reviewed_at: DateTimeField (optional)
```

## Validation Rules

### Amount Validation
- Must be greater than 0
- Cannot exceed user's `template_balance`

### Card Number Validation
- Must be 13-19 digits long
- Must contain only numeric characters (spaces allowed)

### Status Transitions
- **Pending → Approved**: Deducts balance, records reviewer
- **Pending → Rejected**: No balance change, records reason
- **Approved/Rejected → Any**: Not allowed via API (admin only)

## Security Features

### Race Condition Protection
The system uses atomic database operations to prevent race conditions:
- `F()` expressions for balance updates
- `select_for_update()` for row-level locking
- `transaction.atomic()` for transactional integrity

### Authorization
- Users can only view/manage their own withdrawal requests
- Only admins can approve/reject requests
- Commission distribution is automatic and secure

### Validation
- Card number format validation
- Balance sufficiency checks
- Status transition validation

## Example Flow

### Template Sale Flow
1. User purchases template for $100
2. Order status becomes `CONFIRM` with `payment_status=True`
3. Signal triggers automatically
4. Author receives $80 in `template_balance`
5. Platform retains $20 commission

### Withdrawal Flow
1. Author checks balance: `GET /accounts/balance/`
2. Author creates withdrawal request: `POST /template/withdrawal/`
   ```json
   {
     "amount": "500.00",
     "card_number": "8600123456789012",
     "card_owner": "Jane Smith"
   }
   ```
3. Request status: `pending`
4. Admin reviews in Django Admin
5. Admin approves request
6. System deducts $500 from author's `template_balance`
7. Request status: `approved`
8. Admin processes payment to card number offline

## Testing

Comprehensive test coverage includes:
- Withdrawal request creation
- Amount validation
- Card number validation
- User isolation (users can't see others' requests)
- Commission distribution
- Balance accumulation
- Admin approval workflow
- Race condition scenarios

Run tests:
```bash
pytest core/apps/template/tests/withdrawal/
```

## Migration

To apply the database changes:
```bash
python manage.py migrate
```

This will:
1. Add `template_balance` field to User model
2. Add `commission_paid` field to TemplateOrderModel
3. Create `template_withdrawal_request` table

## Monitoring

Monitor the system health:
- Check for pending withdrawals: Filter by status="pending" in admin
- Check commission distribution: Verify `commission_paid=True` on confirmed orders
- Check balance accuracy: Compare sum of approved withdrawals + current balance with total earnings

## Support

For questions or issues:
1. Check this documentation
2. Review test cases in `core/apps/template/tests/withdrawal/`
3. Contact the development team
