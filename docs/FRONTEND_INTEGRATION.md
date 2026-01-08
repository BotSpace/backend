# Template Earnings & Withdrawal System - Frontend Integration Guide

## Umumiy ma'lumot / Overview

Bu hujjat template daromad va pul yechib olish tizimini frontend'ga integratsiya qilish bo'yicha qo'llanma.

This document provides a guide for integrating the template earnings and withdrawal system into the frontend.

---

## API Endpoints

### 1. Balansni tekshirish / Check Balance

**Endpoint:** `GET /accounts/balance/`

**Headers:**
```javascript
{
  "Authorization": "Bearer {access_token}"
}
```

**Response:**
```javascript
{
  "balance": 10000,           // Asosiy balans (tiyin) / Main balance (coins)
  "template_balance": "500.00" // Template balansi (decimal string)
}
```

**Frontend Example (React):**
```javascript
const fetchBalance = async () => {
  const response = await fetch('/accounts/balance/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  const data = await response.json();
  
  // Display balances
  console.log('Main Balance:', data.balance);
  console.log('Template Earnings:', data.template_balance);
};
```

---

### 2. Pul yechib olish so'rovlarini ko'rish / List Withdrawal Requests

**Endpoint:** `GET /template/withdrawal/`

**Headers:**
```javascript
{
  "Authorization": "Bearer {access_token}"
}
```

**Query Parameters:**
- `page` (optional) - Sahifa raqami / Page number
- `page_size` (optional) - Har sahifada nechta / Items per page

**Response:**
```javascript
{
  "status": true,
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 1,
        "amount": "500.00",
        "card_number": "8600123456789012",
        "card_owner": "John Doe",
        "status": "pending",  // pending, approved, rejected
        "rejection_reason": null,
        "created_at": "2026-01-08T10:30:00Z",
        "updated_at": "2026-01-08T10:30:00Z"
      }
    ]
  }
}
```

**Frontend Example (React):**
```javascript
const fetchWithdrawals = async (page = 1) => {
  const response = await fetch(`/template/withdrawal/?page=${page}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  const result = await response.json();
  
  if (result.status) {
    setWithdrawals(result.data.results);
  }
};
```

---

### 3. Pul yechib olish so'rovini yaratish / Create Withdrawal Request

**Endpoint:** `POST /template/withdrawal/`

**Headers:**
```javascript
{
  "Authorization": "Bearer {access_token}",
  "Content-Type": "application/json"
}
```

**Request Body:**
```javascript
{
  "amount": "500.00",              // Decimal string
  "card_number": "8600123456789012", // 13-19 raqam / 13-19 digits
  "card_owner": "John Doe"          // Karta egasi / Card owner name
}
```

**Success Response (201):**
```javascript
{
  "status": true,
  "data": {
    "id": 1,
    "amount": "500.00",
    "card_number": "8600123456789012",
    "card_owner": "John Doe",
    "status": "pending",
    "rejection_reason": null,
    "created_at": "2026-01-08T10:30:00Z",
    "updated_at": "2026-01-08T10:30:00Z"
  }
}
```

**Error Response (400):**
```javascript
{
  "status": false,
  "errors": {
    "amount": ["Insufficient template balance. Available: 200.00"],
    "card_number": ["Card number must be between 13 and 19 digits"]
  }
}
```

**Frontend Example (React):**
```javascript
const createWithdrawal = async (amount, cardNumber, cardOwner) => {
  try {
    const response = await fetch('/template/withdrawal/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        amount: amount,
        card_number: cardNumber,
        card_owner: cardOwner
      })
    });
    
    const result = await response.json();
    
    if (result.status) {
      alert('Withdrawal request created successfully!');
      // Refresh withdrawal list
      fetchWithdrawals();
    } else {
      // Show validation errors
      Object.keys(result.errors).forEach(field => {
        console.error(`${field}: ${result.errors[field].join(', ')}`);
      });
    }
  } catch (error) {
    console.error('Error creating withdrawal:', error);
  }
};
```

---

### 4. So'rovni o'chirish / Delete Withdrawal Request

**Endpoint:** `DELETE /template/withdrawal/{id}/`

**Headers:**
```javascript
{
  "Authorization": "Bearer {access_token}"
}
```

**Success Response (204):** No content

**Error Response (400):**
```javascript
{
  "status": false,
  "errors": {
    "detail": "Cannot delete non-pending withdrawal requests"
  }
}
```

**Frontend Example (React):**
```javascript
const deleteWithdrawal = async (id) => {
  const confirmed = confirm('Are you sure you want to delete this request?');
  if (!confirmed) return;
  
  try {
    const response = await fetch(`/template/withdrawal/${id}/`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (response.status === 204) {
      alert('Withdrawal request deleted successfully!');
      fetchWithdrawals(); // Refresh list
    }
  } catch (error) {
    console.error('Error deleting withdrawal:', error);
  }
};
```

---

## Validatsiya qoidalari / Validation Rules

### Summa / Amount
- ✅ 0 dan katta bo'lishi kerak / Must be greater than 0
- ✅ Template balansidan oshmasligi kerak / Cannot exceed template balance
- ✅ Decimal format (masalan "500.00") / Decimal format (e.g., "500.00")

### Karta raqami / Card Number
- ✅ 13-19 raqamli bo'lishi kerak / Must be 13-19 digits
- ✅ Faqat raqamlar (probel mumkin) / Only numbers (spaces allowed)
- ✅ Format: "8600 1234 5678 9012" yoki "8600123456789012"

### Karta egasi / Card Owner
- ✅ Bo'sh bo'lmasligi kerak / Cannot be empty
- ✅ Maksimal 255 belgi / Maximum 255 characters

---

## Frontend komponentlar namunasi / Sample Frontend Components

### React Component - Withdrawal Request Form

```jsx
import React, { useState, useEffect } from 'react';

const WithdrawalForm = () => {
  const [balance, setBalance] = useState('0.00');
  const [amount, setAmount] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [cardOwner, setCardOwner] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    fetchBalance();
  }, []);

  const fetchBalance = async () => {
    const response = await fetch('/accounts/balance/', {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const data = await response.json();
    setBalance(data.template_balance);
  };

  const formatCardNumber = (value) => {
    // Add spaces every 4 digits
    const cleaned = value.replace(/\s/g, '');
    const formatted = cleaned.match(/.{1,4}/g)?.join(' ') || cleaned;
    return formatted;
  };

  const handleCardNumberChange = (e) => {
    const formatted = formatCardNumber(e.target.value);
    setCardNumber(formatted);
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!amount || parseFloat(amount) <= 0) {
      newErrors.amount = 'Amount must be greater than 0';
    }
    if (parseFloat(amount) > parseFloat(balance)) {
      newErrors.amount = `Insufficient balance. Available: ${balance}`;
    }
    
    const cardDigits = cardNumber.replace(/\s/g, '');
    if (cardDigits.length < 13 || cardDigits.length > 19) {
      newErrors.cardNumber = 'Card number must be 13-19 digits';
    }
    if (!/^\d+$/.test(cardDigits)) {
      newErrors.cardNumber = 'Card number must contain only digits';
    }
    
    if (!cardOwner.trim()) {
      newErrors.cardOwner = 'Card owner name is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    try {
      const response = await fetch('/template/withdrawal/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          amount: amount,
          card_number: cardNumber.replace(/\s/g, ''),
          card_owner: cardOwner
        })
      });
      
      const result = await response.json();
      
      if (result.status) {
        alert('Withdrawal request submitted successfully!');
        // Reset form
        setAmount('');
        setCardNumber('');
        setCardOwner('');
        fetchBalance();
      } else {
        setErrors(result.errors);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="withdrawal-form">
      <h2>Pul yechib olish / Withdraw Earnings</h2>
      
      <div className="balance-display">
        <p>Available Balance: <strong>${balance}</strong></p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Summa / Amount</label>
          <input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="500.00"
            disabled={loading}
          />
          {errors.amount && <span className="error">{errors.amount}</span>}
        </div>

        <div className="form-group">
          <label>Karta raqami / Card Number</label>
          <input
            type="text"
            value={cardNumber}
            onChange={handleCardNumberChange}
            placeholder="8600 1234 5678 9012"
            maxLength="23"
            disabled={loading}
          />
          {errors.cardNumber && <span className="error">{errors.cardNumber}</span>}
        </div>

        <div className="form-group">
          <label>Karta egasi / Card Owner</label>
          <input
            type="text"
            value={cardOwner}
            onChange={(e) => setCardOwner(e.target.value)}
            placeholder="John Doe"
            maxLength="255"
            disabled={loading}
          />
          {errors.cardOwner && <span className="error">{errors.cardOwner}</span>}
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Request'}
        </button>
      </form>
    </div>
  );
};

export default WithdrawalForm;
```

---

### React Component - Withdrawal History

```jsx
import React, { useState, useEffect } from 'react';

const WithdrawalHistory = () => {
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWithdrawals();
  }, []);

  const fetchWithdrawals = async () => {
    setLoading(true);
    try {
      const response = await fetch('/template/withdrawal/', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      const result = await response.json();
      if (result.status) {
        setWithdrawals(result.data.results);
      }
    } catch (error) {
      console.error('Error fetching withdrawals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this request?')) return;
    
    try {
      const response = await fetch(`/template/withdrawal/${id}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      
      if (response.status === 204) {
        alert('Request deleted successfully!');
        fetchWithdrawals();
      }
    } catch (error) {
      console.error('Error deleting withdrawal:', error);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: '⏳ Kutilmoqda / Pending',
      approved: '✅ Tasdiqlangan / Approved',
      rejected: '❌ Rad etilgan / Rejected'
    };
    return badges[status] || status;
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="withdrawal-history">
      <h2>So'rovlar tarixi / Withdrawal History</h2>
      
      {withdrawals.length === 0 ? (
        <p>No withdrawal requests yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Summa / Amount</th>
              <th>Karta / Card</th>
              <th>Holat / Status</th>
              <th>Sana / Date</th>
              <th>Harakatlar / Actions</th>
            </tr>
          </thead>
          <tbody>
            {withdrawals.map((withdrawal) => (
              <tr key={withdrawal.id}>
                <td>{withdrawal.id}</td>
                <td>${withdrawal.amount}</td>
                <td>
                  {withdrawal.card_number}<br/>
                  <small>{withdrawal.card_owner}</small>
                </td>
                <td>
                  <span className={`status-badge ${withdrawal.status}`}>
                    {getStatusBadge(withdrawal.status)}
                  </span>
                  {withdrawal.rejection_reason && (
                    <div className="rejection-reason">
                      Sabab / Reason: {withdrawal.rejection_reason}
                    </div>
                  )}
                </td>
                <td>{new Date(withdrawal.created_at).toLocaleDateString()}</td>
                <td>
                  {withdrawal.status === 'pending' && (
                    <button onClick={() => handleDelete(withdrawal.id)}>
                      O'chirish / Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default WithdrawalHistory;
```

---

## Vue.js Example

```vue
<template>
  <div class="withdrawal-form">
    <h2>Pul yechib olish / Withdraw Earnings</h2>
    
    <div class="balance-display">
      <p>Mavjud balans / Available: <strong>{{ balance }}</strong></p>
    </div>

    <form @submit.prevent="submitWithdrawal">
      <div class="form-group">
        <label>Summa / Amount</label>
        <input
          v-model="form.amount"
          type="number"
          step="0.01"
          placeholder="500.00"
        />
        <span v-if="errors.amount" class="error">{{ errors.amount }}</span>
      </div>

      <div class="form-group">
        <label>Karta raqami / Card Number</label>
        <input
          v-model="form.cardNumber"
          @input="formatCardNumber"
          type="text"
          placeholder="8600 1234 5678 9012"
          maxlength="23"
        />
        <span v-if="errors.cardNumber" class="error">{{ errors.cardNumber }}</span>
      </div>

      <div class="form-group">
        <label>Karta egasi / Card Owner</label>
        <input
          v-model="form.cardOwner"
          type="text"
          placeholder="John Doe"
          maxlength="255"
        />
        <span v-if="errors.cardOwner" class="error">{{ errors.cardOwner }}</span>
      </div>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Yuborilmoqda...' : 'Yuborish / Submit' }}
      </button>
    </form>
  </div>
</template>

<script>
export default {
  data() {
    return {
      balance: '0.00',
      form: {
        amount: '',
        cardNumber: '',
        cardOwner: ''
      },
      errors: {},
      loading: false
    };
  },
  mounted() {
    this.fetchBalance();
  },
  methods: {
    async fetchBalance() {
      const response = await fetch('/accounts/balance/', {
        headers: { 'Authorization': `Bearer ${this.accessToken}` }
      });
      const data = await response.json();
      this.balance = data.template_balance;
    },
    formatCardNumber() {
      const cleaned = this.form.cardNumber.replace(/\s/g, '');
      const formatted = cleaned.match(/.{1,4}/g)?.join(' ') || cleaned;
      this.form.cardNumber = formatted;
    },
    async submitWithdrawal() {
      this.errors = {};
      this.loading = true;
      
      try {
        const response = await fetch('/template/withdrawal/', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            amount: this.form.amount,
            card_number: this.form.cardNumber.replace(/\s/g, ''),
            card_owner: this.form.cardOwner
          })
        });
        
        const result = await response.json();
        
        if (result.status) {
          alert('So\'rov yuborildi! / Request submitted!');
          this.form = { amount: '', cardNumber: '', cardOwner: '' };
          this.fetchBalance();
        } else {
          this.errors = result.errors;
        }
      } catch (error) {
        console.error('Error:', error);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

---

## CSS Styles Example

```css
.withdrawal-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.balance-display {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
  text-align: center;
}

.balance-display strong {
  color: #28a745;
  font-size: 1.5em;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.form-group input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.error {
  color: #dc3545;
  font-size: 14px;
  margin-top: 5px;
  display: block;
}

button[type="submit"] {
  width: 100%;
  padding: 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s;
}

button[type="submit"]:hover {
  background: #0056b3;
}

button[type="submit"]:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

/* Withdrawal History Styles */
.withdrawal-history table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.withdrawal-history th,
.withdrawal-history td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.withdrawal-history th {
  background: #f8f9fa;
  font-weight: 600;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
}

.status-badge.pending {
  background: #ffc107;
  color: #000;
}

.status-badge.approved {
  background: #28a745;
  color: #fff;
}

.status-badge.rejected {
  background: #dc3545;
  color: #fff;
}

.rejection-reason {
  margin-top: 5px;
  font-size: 12px;
  color: #dc3545;
}
```

---

## Muhim eslatmalar / Important Notes

### 1. Xavfsizlik / Security
- ✅ Har doim access token'ni xavfsiz saqlang / Always store access token securely
- ✅ HTTPS ishlatish majburiy / HTTPS is mandatory
- ✅ Token'ni local storage'da saqlashdan ko'ra httpOnly cookie'da saqlash yaxshiroq / Better to use httpOnly cookies instead of localStorage

### 2. Foydalanuvchi tajribasi / User Experience
- ✅ Real-time validatsiya qo'shing / Add real-time validation
- ✅ Loading holatlarini ko'rsating / Show loading states
- ✅ Xato xabarlarni tushunarli qiling / Make error messages clear
- ✅ Muvaffaqiyatli operatsiyalar haqida xabar bering / Show success notifications

### 3. Responsiv dizayn / Responsive Design
- ✅ Mobil qurilmalarda yaxshi ko'rinishi kerak / Must look good on mobile devices
- ✅ Touch-friendly tugmalar / Touch-friendly buttons
- ✅ Formalarni to'ldirish oson bo'lishi kerak / Forms should be easy to fill

---

## Test qilish / Testing

Frontend kodingizni test qilish uchun:

```javascript
// Jest test example
describe('WithdrawalForm', () => {
  it('validates card number correctly', () => {
    const cardNumber = '8600123456789012';
    const isValid = /^\d{13,19}$/.test(cardNumber);
    expect(isValid).toBe(true);
  });

  it('rejects invalid card number', () => {
    const cardNumber = '123';
    const isValid = /^\d{13,19}$/.test(cardNumber);
    expect(isValid).toBe(false);
  });

  it('validates amount against balance', () => {
    const amount = 500;
    const balance = 1000;
    const isValid = amount > 0 && amount <= balance;
    expect(isValid).toBe(true);
  });
});
```

---

## Qo'shimcha resurslar / Additional Resources

- Backend API dokumentatsiyasi: `/docs/TEMPLATE_EARNINGS.md`
- Swagger/OpenAPI: `/api/schema/swagger-ui/`
- Savol-javoblar uchun / For questions: development team

---

**Muallif / Author:** GitHub Copilot  
**Sana / Date:** 2026-01-08  
**Versiya / Version:** 1.0
