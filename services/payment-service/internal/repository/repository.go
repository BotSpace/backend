package repository

import (
	"errors"

	"github.com/botspace/payment-service/internal/models"
	"gorm.io/gorm"
)

// PaymentRepository provides all database operations for the payment service.
type PaymentRepository struct {
	db *gorm.DB
}

// New creates a new PaymentRepository.
func New(db *gorm.DB) *PaymentRepository {
	return &PaymentRepository{db: db}
}

// AutoMigrate runs GORM auto-migration for all payment models.
func AutoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(
		&models.Transaction{},
		&models.History{},
	)
}

// ---- Transactions ----

func (r *PaymentRepository) CreateTransaction(t *models.Transaction) error {
	return r.db.Create(t).Error
}

func (r *PaymentRepository) GetTransaction(id, userID uint) (*models.Transaction, error) {
	var t models.Transaction
	return &t, r.db.Where("id = ? AND user_id = ?", id, userID).First(&t).Error
}

func (r *PaymentRepository) ListTransactions(userID uint) ([]models.Transaction, error) {
	var items []models.Transaction
	return items, r.db.Where("user_id = ?", userID).Find(&items).Error
}

// MarkTransactionComplete sets the transaction status to true (paid).
func (r *PaymentRepository) MarkTransactionComplete(id uint) error {
	return r.db.Model(&models.Transaction{}).Where("id = ?", id).Update("status", true).Error
}

// GetTransactionByIDOnly retrieves a transaction by its ID (used by webhook handlers).
func (r *PaymentRepository) GetTransactionByIDOnly(id uint) (*models.Transaction, error) {
	var t models.Transaction
	if err := r.db.First(&t, id).Error; err != nil {
		return nil, err
	}
	return &t, nil
}

// ---- History ----

func (r *PaymentRepository) CreateHistory(h *models.History) error {
	return r.db.Create(h).Error
}

func (r *PaymentRepository) GetHistory(id, userID uint) (*models.History, error) {
	var h models.History
	return &h, r.db.Where("id = ? AND user_id = ?", id, userID).First(&h).Error
}

func (r *PaymentRepository) ListHistory(userID uint) ([]models.History, error) {
	var items []models.History
	return items, r.db.Where("user_id = ?", userID).Order("created_at DESC").Find(&items).Error
}

// ---- Balance helpers ----

// AddBalance records an income history entry.
func (r *PaymentRepository) AddBalance(userID uint, amount float64, comment string) error {
	if amount <= 0 {
		return errors.New("amount must be positive")
	}
	return r.CreateHistory(&models.History{
		UserID:  userID,
		Amount:  amount,
		Type:    models.HistoryTypeIncome,
		Comment: comment,
	})
}

// SubtractBalance records an expense history entry.
func (r *PaymentRepository) SubtractBalance(userID uint, amount float64, comment string) error {
	if amount <= 0 {
		return errors.New("amount must be positive")
	}
	return r.CreateHistory(&models.History{
		UserID:  userID,
		Amount:  amount,
		Type:    models.HistoryTypeExpense,
		Comment: comment,
	})
}
