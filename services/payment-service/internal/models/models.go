package models

import (
	"time"

	"gorm.io/gorm"
)

// Transaction records a payment attempt.
type Transaction struct {
	ID        uint           `gorm:"primaryKey"                        json:"id"`
	UserID    uint           `gorm:"not null;index"                    json:"user_id"`
	Amount    float64        `gorm:"type:decimal(20,2);not null"       json:"amount"`
	Status    bool           `gorm:"default:false"                     json:"status"`
	OrderID   *uint          `gorm:"index"                             json:"order_id,omitempty"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index"                             json:"-"`
}

// HistoryType enumerates balance change directions.
type HistoryType string

const (
	HistoryTypeIncome  HistoryType = "income"
	HistoryTypeExpense HistoryType = "expense"
)

// History records a balance change for a user.
type History struct {
	ID        uint           `gorm:"primaryKey"                        json:"id"`
	UserID    uint           `gorm:"not null;index"                    json:"user_id"`
	Amount    float64        `gorm:"type:decimal(30,2);not null"       json:"amount"`
	Type      HistoryType    `gorm:"size:20;not null"                  json:"type"`
	Comment   string         `gorm:"size:255"                          json:"comment,omitempty"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index"                             json:"-"`
}
